import logging
import random
import threading
import time
from collections import Counter, defaultdict, deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, as_completed, wait
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, field
from datetime import UTC, datetime

from .checks import ERROR, Resultado
from .checks import dns as checks_dns
from .checks import web as checks_web
from .dominios import Entidade, alternativo, coordenada, dominio_email, fora_do_gov_br
from .nota import METODOLOGIA, PESOS, calcular_nota, conceito

log = logging.getLogger(__name__)

# avisos sobre a qualidade do dado (nao sao falhas de seguranca)
NAO_RESOLVE = "nao_resolve"
ALTERNATIVO = "dominio_alternativo"
FORA_GOV_BR = "fora_do_gov_br"
COMPARTILHADO = "dominio_compartilhado"
INCOMPLETA = "verificacao_incompleta"

# com esses avisos o municipio fica fora do ranking ate alguem confirmar o dominio
TIRA_DO_RANKING = {FORA_GOV_BR, COMPARTILHADO}

CHECKS_DNS = ("dnssec", "caa", "spf", "dmarc")

# erros que valem uma segunda tentativa, com mais calma (timeout, servidor sobrecarregado)
ERROS_TRANSITORIOS = ("timeout", "outro", "LifetimeTimeout", "NoNameservers")


class LimitePorServidor:
    """Muitas prefeituras ficam no mesmo servidor (empresa de hospedagem, datacenter do estado).

    Sem limite, 32 threads batiam no mesmo IP ao mesmo tempo, o servidor passava a
    recusar ou demorar e a prefeitura levava timeout. Aqui cada IP aceita poucas
    verificacoes simultaneas.
    """

    def __init__(self, por_ip=3):
        self.por_ip = por_ip
        self._trava = threading.Lock()
        self._sem = defaultdict(lambda: threading.Semaphore(self.por_ip))

    @contextmanager
    def __call__(self, ip):
        with self._trava:
            sem = self._sem[ip]
        with sem:
            yield


@dataclass
class Preparo:
    """Tudo que depende so de DNS. Sai antes da parte web pra gente saber o IP de cada
    site e conseguir distribuir as visitas sem empilhar threads no mesmo servidor."""

    entidade: Entidade
    host: str
    existe: bool
    ips: list
    avisos: list
    dns: list = field(default_factory=list)

    @property
    def servidor(self):
        """Chave da fila de visitas: o IP, ou o proprio host se o DNS nao deu IP."""
        if not self.existe:
            return None
        return self.ips[0] if self.ips else self.host


def preparar(entidade, resolver):
    host = entidade.dominio
    avisos = []

    existe, dnssec, ips = checks_dns.checar_dnssec(host, resolver)
    if not existe:
        alt = alternativo(host)
        existe_alt, dnssec_alt, ips_alt = checks_dns.checar_dnssec(alt, resolver)
        if existe_alt:
            host, existe, dnssec, ips = alt, True, dnssec_alt, ips_alt
            avisos.append(ALTERNATIVO)
        else:
            avisos.append(NAO_RESOLVE)

    if fora_do_gov_br(host):
        avisos.append(FORA_GOV_BR)

    email = dominio_email(host)
    dns = [
        dnssec,
        checks_dns.checar_caa(email, resolver),
        checks_dns.checar_spf(email, resolver),
        checks_dns.checar_dmarc(email, resolver),
    ]
    return Preparo(entidade, host, existe, list(ips or []), avisos, dns)


def visitar(prep, cliente):
    """Parte web. Devolve (acessivel, resultados)."""
    if not prep.existe:
        return False, [Resultado(nome, ERROR, "dominio nao resolve") for nome in PESOS if nome not in CHECKS_DNS]
    return checks_web.checar_web(prep.host, cliente)


def sem_tempo(prep):
    """Quando o prazo da varredura acaba antes de visitar o site: fica sem nota nesta rodada."""
    return com_erro(prep, "prazo: a varredura acabou antes de chegar neste site")


def com_erro(prep, motivo):
    return True, [Resultado(nome, ERROR, motivo) for nome in PESOS if nome not in CHECKS_DNS]


def montar(prep, acessivel, web):
    ent = prep.entidade
    avisos = list(prep.avisos)
    resultados = prep.dns + web
    nota = calcular_nota(resultados) if acessivel else None
    if acessivel and nota is None:
        avisos.append(INCOMPLETA)

    por_nome = {r.check: r for r in resultados}
    return {
        "ibge": ent.ibge,
        "municipio": ent.municipio,
        "uf": ent.uf,
        "lat": coordenada(ent.lat),
        "lon": coordenada(ent.lon),
        "dominio": prep.host,
        "dominio_wikidata": ent.dominio,
        "ip": prep.ips[0] if prep.ips else None,
        "acessivel": acessivel,
        "ranking": nota is not None and not TIRA_DO_RANKING.intersection(avisos),
        "nota": nota,
        "conceito": conceito(nota) if nota is not None else None,
        "avisos": avisos,
        # sempre na ordem dos PESOS, que e a ordem da pagina
        "checks": {n: {"status": por_nome[n].status, "detalhe": por_nome[n].detalhe} for n in PESOS if n in por_nome},
    }


def avaliar(entidade, resolver, cliente, limite=None):
    prep = preparar(entidade, resolver)
    with limite(prep.servidor) if (limite and prep.servidor) else nullcontext():
        acessivel, web = visitar(prep, cliente)
    return montar(prep, acessivel, web)


def erros_transitorios(resultado):
    return sum(
        1 for c in resultado["checks"].values()
        if c["status"] == ERROR and c["detalhe"].startswith(ERROS_TRANSITORIOS)
    )


def marcar_compartilhados(resultados):
    """Mesmo dominio pra mais de um municipio quase sempre e erro no cadastro (site de associacao etc)."""
    contagem = Counter(r["dominio"] for r in resultados)
    for r in resultados:
        if contagem[r["dominio"]] > 1 and COMPARTILHADO not in r["avisos"]:
            r["avisos"].append(COMPARTILHADO)
            r["ranking"] = False


def _rodar(entidades, resolver_factory, cliente, workers, por_ip, progresso=None, prazo=None):
    """Avalia em duas fases e devolve (resultados, ibges que ficaram sem visita por prazo).

    1. DNS de todo mundo, em paralelo (rapido, vai nos resolvers publicos).
    2. Visita aos sites com uma fila por IP: no maximo `por_ip` visitas ao mesmo
       servidor ao mesmo tempo, e a proxima so entra quando uma termina.

    Antes a fase 2 usava um semaforo dentro de cada thread. Quando um servidor de
    hospedagem com centenas de prefeituras ficava lento, as 32 threads iam parando uma
    a uma esperando a vez dele e a varredura inteira se arrastava.

    Com `prazo` (segundos), quem nao foi visitado a tempo sai sem nota nesta rodada.
    """
    fim = time.monotonic() + prazo if prazo else None
    restante = lambda: None if fim is None else max(0.0, fim - time.monotonic())  # noqa: E731
    total = len(entidades)
    feitos = 0

    def avancou():
        nonlocal feitos
        feitos += 1
        if progresso:
            progresso(feitos, total)

    # fase 1: dns. dnspython nao garante ser thread-safe, entao cada tarefa cria o seu resolver
    preparos = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futuros = {pool.submit(preparar, e, resolver_factory()): e for e in entidades}
        for fut in as_completed(futuros):
            try:
                preparos.append(fut.result())
            except Exception:
                log.exception("erro inesperado no dns de %s", futuros[fut].dominio)
    # devolve a ordem original (as_completed embaralha conforme quem termina primeiro)
    posicao = {e.ibge: i for i, e in enumerate(entidades)}
    preparos.sort(key=lambda p: posicao[p.entidade.ibge])

    resultados = {}
    filas = defaultdict(deque)
    for prep in preparos:
        if prep.servidor is None:
            # nem resolveu: nao tem site pra visitar
            resultados[prep.entidade.ibge] = montar(prep, *visitar(prep, cliente))
            avancou()
        else:
            filas[prep.servidor].append(prep)

    def tarefa(prep):
        inicio = time.monotonic()
        acessivel, web = visitar(prep, cliente)
        gasto = time.monotonic() - inicio
        if gasto > 90:
            log.warning("lento: %s (%s) levou %.0fs", prep.host, prep.servidor, gasto)
        return montar(prep, acessivel, web)

    # fase 2: visitas. a primeira leva intercala os IPs (rodada 1: um de cada servidor,
    # rodada 2: o segundo de cada um...) pra servidor grande nao ocupar o comeco da fila
    pool = ThreadPoolExecutor(max_workers=workers)
    andando = {}

    def mandar(ip):
        prep = filas[ip].popleft()
        andando[pool.submit(tarefa, prep)] = prep

    for _ in range(por_ip):
        for ip in list(filas):
            if filas[ip]:
                mandar(ip)

    sem_prazo = set()
    try:
        while andando:
            prontos, _ = wait(andando, timeout=restante(), return_when=FIRST_COMPLETED)
            if not prontos:
                break  # prazo acabou
            for fut in prontos:
                prep = andando.pop(fut)
                try:
                    resultados[prep.entidade.ibge] = fut.result()
                except Exception:
                    log.exception("erro inesperado em %s", prep.host)
                    resultados[prep.entidade.ibge] = montar(prep, *com_erro(prep, "erro inesperado na verificacao"))
                avancou()
                if filas[prep.servidor]:
                    mandar(prep.servidor)
    finally:
        pool.shutdown(wait=fim is None, cancel_futures=True)

    # o que nao deu tempo: o dns ja foi feito, so a visita ficou faltando
    for prep in [*andando.values(), *(p for fila in filas.values() for p in fila)]:
        resultados[prep.entidade.ibge] = montar(prep, *sem_tempo(prep))
        sem_prazo.add(prep.entidade.ibge)
    if sem_prazo:
        log.warning("prazo de %ss acabou: %d sites ficaram sem visita", prazo, len(sem_prazo))
    return resultados, sem_prazo


def varrer(entidades, resolver_factory, cliente, workers=32, progresso=None, cliente_lento=None, por_ip=3, prazo=75 * 60, prazo_repescagem=600):
    """Roda avaliar() em paralelo, com uma repescagem no fim pra quem deu timeout.

    resolver_factory cria um resolver por tarefa. cliente_lento (timeout maior) e usado
    so na repescagem; se nao vier, a repescagem usa o mesmo cliente. As duas passadas
    tem prazo pra caber com folga no job do Actions (na de 17/11 a repescagem sozinha
    passou de 50 minutos e a varredura nao terminou).
    """
    # embaralha com semente fixa: a lista vem por codigo IBGE, o que junta cidades do mesmo
    # estado (e muitas vezes do mesmo servidor) uma atras da outra
    ordem = list(entidades)
    random.Random(0).shuffle(ordem)

    resultados, sem_prazo = _rodar(ordem, resolver_factory, cliente, workers, por_ip, progresso, prazo=prazo)

    # se a primeira passada ja estourou o prazo, nao tem tempo pra repescagem
    pendentes = [] if sem_prazo else [e for e in ordem if e.ibge in resultados and erros_transitorios(resultados[e.ibge])]
    repescados = 0
    sem_resposta = 0
    if pendentes:
        log.warning("repescagem: %d dominios com timeout, tentando de novo com mais calma", len(pendentes))
        # 2 por IP: com 1 so, um servidor com centenas de prefeituras virava fila de horas
        segunda, nao_visitados = _rodar(pendentes, resolver_factory, cliente_lento or cliente, max(2, workers // 4), 2, prazo=prazo_repescagem)
        sem_resposta = len(nao_visitados)
        for ibge, novo in segunda.items():
            # quem ficou sem visita na repescagem mantem o resultado da primeira passada
            if ibge not in nao_visitados and erros_transitorios(novo) < erros_transitorios(resultados[ibge]):
                resultados[ibge] = novo
                repescados += 1

    lista = sorted(resultados.values(), key=lambda r: r["ibge"])
    marcar_compartilhados(lista)
    return {
        "gerado_em": datetime.now(UTC).isoformat(timespec="seconds"),
        "metodologia": METODOLOGIA,
        "total": len(lista),
        "sem_visita_por_prazo": len(sem_prazo),
        "repescagem": {"tentados": len(pendentes), "recuperados": repescados, "fora_do_prazo": sem_resposta},
        "resultados": lista,
    }
