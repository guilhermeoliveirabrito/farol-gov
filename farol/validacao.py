"""Confere se uma varredura esta boa o bastante pra ir pro historico e pro site.

Uma rodada ruim (runner bloqueado, DNS fora do ar, prazo estourado) nao pode
sobrescrever os dados bons da semana anterior: as setas e o grafico iam mostrar
centenas de cidades "caindo" sem nada ter mudado nos sites delas.
"""

from . import historico
from .scanner import INCOMPLETA

# limites folgados: uma semana normal fica longe deles
MIN_TOTAL = 0.98  # da lista anterior
MIN_ACESSIVEIS = 0.90  # dos sites que responderam na anterior
MAX_INCOMPLETAS = 0.08  # dos que responderam
MAX_SEM_VISITA = 0.02  # do total, por prazo estourado


def _pct(x):
    return f"{100 * x:.1f}%".replace(".", ",")


def validar(dados, snapshots):
    """Devolve (problemas, linhas do relatorio). Sem problemas = pode publicar."""
    resultados = dados["resultados"]
    total = len(resultados)
    acessiveis = sum(1 for r in resultados if r.get("acessivel"))
    incompletas = sum(1 for r in resultados if INCOMPLETA in r.get("avisos", []))
    sem_visita = dados.get("sem_visita_por_prazo", 0)

    linhas = [
        f"- municipios: {total}",
        f"- sites que responderam: {acessiveis}",
        f"- verificacao incompleta: {incompletas} ({_pct(incompletas / acessiveis) if acessiveis else '-'})",
        f"- sem visita por prazo: {sem_visita}",
    ]
    problemas = []
    if not total:
        return ["a varredura nao tem nenhum resultado"], linhas
    if acessiveis and incompletas / acessiveis > MAX_INCOMPLETAS:
        problemas.append(f"{_pct(incompletas / acessiveis)} dos sites ficaram com verificacao incompleta (limite {_pct(MAX_INCOMPLETAS)})")
    if sem_visita / total > MAX_SEM_VISITA:
        problemas.append(f"{sem_visita} sites ficaram sem visita porque o prazo acabou")

    dia = historico.dia_da_varredura(dados.get("gerado_em"))
    anteriores = [s for s in snapshots if s["data"] < dia]
    if anteriores:
        antes = anteriores[-1]
        total_antes = len(antes["m"])
        acessiveis_antes = sum(1 for flags, _ in antes["m"].values() if flags & historico.ACESSIVEL)
        linhas.append(f"- comparando com {antes['data']}: {total_antes} municipios, {acessiveis_antes} responderam")
        if total < MIN_TOTAL * total_antes:
            problemas.append(f"so {total} municipios, contra {total_antes} na varredura de {antes['data']}")
        if acessiveis_antes and acessiveis < MIN_ACESSIVEIS * acessiveis_antes:
            problemas.append(f"so {acessiveis} sites responderam, contra {acessiveis_antes} em {antes['data']}")
    return problemas, linhas
