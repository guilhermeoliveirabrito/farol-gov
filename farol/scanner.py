import logging
import random
import threading
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager, nullcontext
from datetime import UTC, datetime

from .checks import ERROR, Resultado
from .checks import dns as checks_dns
from .checks import web as checks_web
from .dominios import alternativo, coordenada, dominio_email, fora_do_gov_br
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


def avaliar(entidade, resolver, cliente, limite=None):
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

    resultados = [dnssec]
    if existe:
        with limite(ips[0]) if (limite and ips) else nullcontext():
            acessivel, web = checks_web.checar_web(host, cliente)
        resultados += web
    else:
        acessivel = False
        resultados += [Resultado(nome, ERROR, "dominio nao resolve") for nome in PESOS if nome not in CHECKS_DNS]

    email = dominio_email(host)
    resultados.append(checks_dns.checar_caa(email, resolver))
    resultados.append(checks_dns.checar_spf(email, resolver))
    resultados.append(checks_dns.checar_dmarc(email, resolver))

    nota = calcular_nota(resultados) if acessivel else None
    if acessivel and nota is None:
        avisos.append(INCOMPLETA)

    por_nome = {r.check: r for r in resultados}
    return {
        "ibge": entidade.ibge,
        "municipio": entidade.municipio,
        "uf": entidade.uf,
        "lat": coordenada(entidade.lat),
        "lon": coordenada(entidade.lon),
        "dominio": host,
        "dominio_wikidata": entidade.dominio,
        "ip": ips[0] if ips else None,
        "acessivel": acessivel,
        "ranking": nota is not None and not TIRA_DO_RANKING.intersection(avisos),
        "nota": nota,
        "conceito": conceito(nota) if nota is not None else None,
        "avisos": avisos,
        # sempre na ordem dos PESOS, que e a ordem da pagina
        "checks": {n: {"status": por_nome[n].status, "detalhe": por_nome[n].detalhe} for n in PESOS if n in por_nome},
    }


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


def _rodar(entidades, resolver_factory, cliente, workers, limite, progresso=None):
    resultados = {}

    # dnspython nao garante ser thread-safe, entao cada tarefa cria o seu resolver
    def tarefa(ent):
        return avaliar(ent, resolver_factory(), cliente, limite)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futuros = {pool.submit(tarefa, e): e for e in entidades}
        for i, fut in enumerate(as_completed(futuros), 1):
            ent = futuros[fut]
            try:
                resultados[ent.ibge] = fut.result()
            except Exception:
                # nao deixa um dominio estranho derrubar a varredura inteira
                log.exception("erro inesperado em %s", ent.dominio)
            if progresso:
                progresso(i, len(futuros))
    return resultados


def varrer(entidades, resolver_factory, cliente, workers=32, progresso=None, cliente_lento=None, por_ip=3):
    """Roda avaliar() em paralelo, com uma repescagem no fim pra quem deu timeout.

    resolver_factory cria um resolver por tarefa. cliente_lento (timeout maior) e usado
    so na repescagem; se nao vier, a repescagem usa o mesmo cliente.
    """
    # embaralha com semente fixa: a lista vem por codigo IBGE, o que junta cidades do mesmo
    # estado (e muitas vezes do mesmo servidor) uma atras da outra
    ordem = list(entidades)
    random.Random(0).shuffle(ordem)

    resultados = _rodar(ordem, resolver_factory, cliente, workers, LimitePorServidor(por_ip), progresso)

    pendentes = [e for e in ordem if e.ibge in resultados and erros_transitorios(resultados[e.ibge])]
    repescados = 0
    if pendentes:
        log.warning("repescagem: %d dominios com timeout, tentando de novo com mais calma", len(pendentes))
        # 2 por IP: com 1 so, um servidor com centenas de prefeituras virava fila de horas
        segunda = _rodar(pendentes, resolver_factory, cliente_lento or cliente, max(2, workers // 4), LimitePorServidor(2))
        for ibge, novo in segunda.items():
            if erros_transitorios(novo) < erros_transitorios(resultados[ibge]):
                resultados[ibge] = novo
                repescados += 1

    lista = sorted(resultados.values(), key=lambda r: r["ibge"])
    marcar_compartilhados(lista)
    return {
        "gerado_em": datetime.now(UTC).isoformat(timespec="seconds"),
        "metodologia": METODOLOGIA,
        "total": len(lista),
        "repescagem": {"tentados": len(pendentes), "recuperados": repescados},
        "resultados": lista,
    }
