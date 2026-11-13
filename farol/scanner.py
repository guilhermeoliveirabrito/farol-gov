import logging
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from .checks import ERROR, Resultado
from .checks import dns as checks_dns
from .checks import web as checks_web
from .dominios import alternativo, dominio_email, fora_do_gov_br
from .nota import PESOS, calcular_nota, conceito

log = logging.getLogger(__name__)

# avisos sobre a qualidade do dado (nao sao falhas de seguranca)
NAO_RESOLVE = "nao_resolve"
ALTERNATIVO = "dominio_alternativo"
FORA_GOV_BR = "fora_do_gov_br"
COMPARTILHADO = "dominio_compartilhado"

# com esses avisos o municipio fica fora do ranking ate alguem confirmar o dominio
TIRA_DO_RANKING = {FORA_GOV_BR, COMPARTILHADO}


def avaliar(entidade, resolver, cliente):
    host = entidade.dominio
    avisos = []

    existe, dnssec = checks_dns.checar_dnssec(host, resolver)
    if not existe:
        alt = alternativo(host)
        existe_alt, dnssec_alt = checks_dns.checar_dnssec(alt, resolver)
        if existe_alt:
            host, existe, dnssec = alt, True, dnssec_alt
            avisos.append(ALTERNATIVO)
        else:
            avisos.append(NAO_RESOLVE)

    if fora_do_gov_br(host):
        avisos.append(FORA_GOV_BR)

    resultados = [dnssec]
    if existe:
        acessivel, web = checks_web.checar_web(host, cliente)
        resultados += web
    else:
        acessivel = False
        resultados += [
            Resultado(nome, ERROR, "dominio nao resolve")
            for nome in PESOS
            if nome not in ("dnssec", "spf", "dmarc")
        ]

    email = dominio_email(host)
    resultados.append(checks_dns.checar_spf(email, resolver))
    resultados.append(checks_dns.checar_dmarc(email, resolver))

    nota = calcular_nota(resultados) if acessivel else None
    return {
        "ibge": entidade.ibge,
        "municipio": entidade.municipio,
        "uf": entidade.uf,
        "dominio": host,
        "dominio_wikidata": entidade.dominio,
        "acessivel": acessivel,
        "ranking": acessivel and not TIRA_DO_RANKING.intersection(avisos),
        "nota": nota,
        "conceito": conceito(nota) if nota is not None else None,
        "avisos": avisos,
        "checks": {r.check: {"status": r.status, "detalhe": r.detalhe} for r in resultados},
    }


def marcar_compartilhados(resultados):
    """Mesmo dominio pra mais de um municipio quase sempre e erro no cadastro (site de associacao etc)."""
    contagem = Counter(r["dominio"] for r in resultados)
    for r in resultados:
        if contagem[r["dominio"]] > 1 and COMPARTILHADO not in r["avisos"]:
            r["avisos"].append(COMPARTILHADO)
            r["ranking"] = False


def varrer(entidades, resolver_factory, cliente, workers=32, progresso=None):
    """Roda avaliar() em paralelo. resolver_factory cria um resolver por thread."""
    resultados = []
    # dnspython nao garante ser thread-safe, entao cada tarefa cria o seu
    def tarefa(ent):
        return avaliar(ent, resolver_factory(), cliente)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futuros = {pool.submit(tarefa, e): e for e in entidades}
        for i, fut in enumerate(as_completed(futuros), 1):
            ent = futuros[fut]
            try:
                resultados.append(fut.result())
            except Exception:
                # nao deixa um dominio estranho derrubar a varredura inteira
                log.exception("erro inesperado em %s", ent.dominio)
            if progresso:
                progresso(i, len(futuros))

    marcar_compartilhados(resultados)
    resultados.sort(key=lambda r: r["ibge"])
    return {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": len(resultados),
        "resultados": resultados,
    }
