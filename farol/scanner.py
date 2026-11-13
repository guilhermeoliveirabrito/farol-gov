import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from .checks import ERROR, Resultado
from .checks import dns as checks_dns
from .checks import web as checks_web
from .dominios import dominio_email
from .nota import PESOS, calcular_nota, conceito

log = logging.getLogger(__name__)


def avaliar(entidade, resolver, cliente):
    host = entidade.dominio
    email = dominio_email(host)

    existe, dnssec = checks_dns.checar_dnssec(host, resolver)
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

    resultados.append(checks_dns.checar_spf(email, resolver))
    resultados.append(checks_dns.checar_dmarc(email, resolver))

    nota = calcular_nota(resultados) if acessivel else None
    return {
        "ibge": entidade.ibge,
        "municipio": entidade.municipio,
        "uf": entidade.uf,
        "dominio": host,
        "acessivel": acessivel,
        "nota": nota,
        "conceito": conceito(nota) if nota is not None else None,
        "checks": {r.check: {"status": r.status, "detalhe": r.detalhe} for r in resultados},
    }


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

    resultados.sort(key=lambda r: r["ibge"])
    return {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": len(resultados),
        "resultados": resultados,
    }
