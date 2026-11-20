"""Histórico semanal da varredura.

Cada semana vira um arquivo pequeno em data/historico/AAAA-MM-DD.json com só o
necessário pra recalcular nota e posição: o status de cada item, por município.
O json completo (uns 4 MB) fica só no latest.json, pra não inchar o repositório.

A nota de semanas antigas é sempre recalculada com as regras atuais (farol.nota),
assim a série fica comparável. Itens que ainda não existiam numa semana simplesmente
não entram na conta daquela semana.
"""
import json
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from .checks import Resultado
from .dominios import uf_do_ibge
from .nota import calcular_nota, conceito, grau, pontos_de_detalhe

CODIGO = {"pass": "p", "warn": "w", "fail": "f", "error": "e"}
# grau de cada item em passos de 0,05: "a" = 0, "u" = 1
GRAUS = "abcdefghijklmnopqrstu"
STATUS = {v: k for k, v in CODIGO.items()}

ACESSIVEL = 1
ELEGIVEL = 2  # sem aviso que tira do ranking (dominio fora do .gov.br, repetido...)

AVISOS_FORA = {"fora_do_gov_br", "dominio_compartilhado"}

# o Brasil nao tem mais horario de verao desde 2019, entao -3 fixo resolve sem depender de tzdata
BRASILIA = timezone(timedelta(hours=-3))


def dia_da_varredura(gerado_em):
    """Data (no horario de Brasilia) que identifica a varredura no historico.

    Uma varredura por dia: se rodar de novo no mesmo dia, o arquivo daquele dia e
    substituido, entao o grafico nunca tem dois pontos na mesma data.
    """
    try:
        momento = datetime.fromisoformat(gerado_em)
    except (TypeError, ValueError):
        return str(gerado_em)[:10]
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=UTC)
    return momento.astimezone(BRASILIA).date().isoformat()


def compactar(dados):
    """Transforma o json da varredura no formato do historico."""
    checks = []
    for r in dados["resultados"]:
        for c in r.get("checks", {}):
            if c not in checks:
                checks.append(c)
    municipios = {}
    for r in dados["resultados"]:
        flags = ACESSIVEL if r.get("acessivel") else 0
        if not AVISOS_FORA.intersection(r.get("avisos", [])):
            flags |= ELEGIVEL
        status = "".join(CODIGO.get(r["checks"].get(c, {}).get("status"), "-") for c in checks)
        graus = "".join(
            GRAUS[round(20 * grau(c, r["checks"][c].get("status"), r["checks"][c].get("detalhe", "")))] if c in r["checks"] else "-"
            for c in checks
        )
        # 4o: grau de cada item (metodologia 3). 5o: ip, pra saber quem divide servidor
        # 3o: pontos de detalhe (metodologia 5; antes era a contagem de excelencia)
        municipios[r["ibge"]] = [flags, status, pontos_de_detalhe(r.get("checks", {})), graus, r.get("ip") or ""]
    return {
        "data": dia_da_varredura(dados["gerado_em"]),
        "metodologia": dados.get("metodologia", 1),
        # o 3o campo de cada cidade sao pontos de detalhe (antes era contagem de excelencia)
        "detalhes": 1,
        "checks": checks,
        "m": municipios,
    }


def salvar(dados, pasta):
    """Grava a varredura em data/historico/AAAA-MM-DD.json, substituindo a do mesmo dia."""
    snap = compactar(dados)
    destino = Path(pasta) / f"{snap['data']}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(snap, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return destino


def carregar(pasta):
    """Snapshots em ordem de data."""
    pasta = Path(pasta)
    if not pasta.exists():
        return []
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(pasta.glob("*.json"))]


def nota_do_status(checks, status, graus=""):
    """Nota base a partir do status de cada item. Os graus guardados pelas metodologias 3
    e 4 ficam no arquivo, mas a nota base voltou a ser so cumpre/parcial/nao cumpre."""
    resultados = [Resultado(c, STATUS[s]) for c, s in zip(checks, status) if s in STATUS]
    return calcular_nota(resultados)


def posicoes(notas):
    """Posicao no ranking, com empate dividindo a mesma posicao (1, 2, 2, 4...).

    `notas` pode ter numero ou tupla (nota e os criterios de desempate)."""
    ordem = sorted(notas.values(), reverse=True)
    primeira = {}
    for i, n in enumerate(ordem, 1):
        primeira.setdefault(n, i)
    return {ibge: primeira[n] for ibge, n in notas.items()}


# o que separa duas cidades, nessa ordem: a 1a posicao da chave e a nota base, a 2a os
# pontos de detalhe (que sao somados a nota pra ordenar: chave[0] e o total)
CRITERIOS = (
    "nota",
    "mais pontos de detalhe",
    "mais itens cumpridos por inteiro",
    "maior população (mais gente protegida)",
)


def detalhes_do_snapshot(snap, linha):
    """Pontos de detalhe guardados no historico (so a partir da metodologia 5)."""
    if not snap.get("detalhes") or len(linha) < 3 or not isinstance(linha[2], (int, float)):
        return 0.0
    return float(linha[2])


def chave(nota, status, detalhes, populacao):
    """Chave do ranking: (nota + detalhes, nota, itens inteiros, populacao).

    A nota base mede o essencial; os detalhes somam poucos pontos por cima e separam
    quem fez o essencial igual. Se ainda assim empatar (24 prefeituras de SE no mesmo
    servidor do estado, com o site montado igual), fica na frente quem tem mais itens
    cumpridos por inteiro e, por ultimo, quem protege mais gente."""
    detalhes = detalhes or 0.0
    return (round(nota + detalhes, 2), nota, str(status).count("p"), populacao or 0)


def criterio_do_desempate(a, b):
    """Qual criterio separou a chave a da b (None se nao foi desempate de nota igual)."""
    if a[1] != b[1]:
        return None  # nota base diferente: nao foi desempate
    if a[0] != b[0]:
        return CRITERIOS[1]
    if a[2] != b[2]:
        return CRITERIOS[2]
    if a[3] != b[3]:
        return CRITERIOS[3]
    return None


def avaliar_snapshot(snap, populacao=None):
    """Devolve {ibge: [nota, conceito, posicao oficial, posicao geral, pontos de detalhe]} com as regras atuais.

    Ranking oficial: so quem teve todos os itens daquela varredura verificados. Item nao
    verificado sai da conta da nota, entao quem teve item sem resposta pode ficar com
    nota maior do que a real; essas cidades entram so no ranking geral.
    """
    checks = snap["checks"]
    geral, oficial, saida = {}, {}, {}
    for ibge, (flags, status, *resto) in snap["m"].items():
        graus = resto[1] if len(resto) > 1 else ""
        nota = nota_do_status(checks, status, graus) if flags & ACESSIVEL else None
        detalhes = detalhes_do_snapshot(snap, [flags, status, *resto]) if nota is not None else None
        saida[ibge] = [nota, conceito(nota) if nota is not None else None, None, None, detalhes]
        if nota is not None and flags & ELEGIVEL:
            k = chave(nota, status, detalhes, (populacao or {}).get(ibge))
            geral[ibge] = k
            if "e" not in status:
                oficial[ibge] = k
    for ibge, pos in posicoes(oficial).items():
        saida[ibge][2] = pos
    for ibge, pos in posicoes(geral).items():
        saida[ibge][3] = pos
    return saida


def resumo_nacional(snap, avaliacao):
    """Uma linha do grafico de evolucao: media, conceitos e adocao de cada item."""
    # media e adocao usam todo mundo com nota (ranking geral), pra serie nao mudar de base
    ranqueados = [i for i, v in avaliacao.items() if v[3] is not None]
    n = len(ranqueados)
    if not n:
        return None
    conceitos = dict.fromkeys("ABCDF", 0)
    for i in ranqueados:
        conceitos[avaliacao[i][1]] += 1
    por_uf = {}
    for i in ranqueados:
        por_uf.setdefault(uf_do_ibge(i), []).append(avaliacao[i][0])
    adocao = {}
    for j, c in enumerate(snap["checks"]):
        cumpre = sum(1 for i in ranqueados if snap["m"][i][1][j] == "p")
        adocao[c] = round(100 * cumpre / n, 1)
    return {
        "data": snap["data"],
        "metodologia": snap.get("metodologia", 1),
        "n": n,
        "media": round(sum(avaliacao[i][0] for i in ranqueados) / n, 1),
        "conceitos": conceitos,
        "adocao": adocao,
        "ufs": {uf: round(sum(v) / len(v), 2) for uf, v in sorted(por_uf.items()) if uf},
    }


def variacoes(anterior, atual):
    """Quem subiu e quem caiu entre duas semanas: lista de (ibge, pos_antes, pos_agora)."""
    mudancas = []
    for ibge, (_, _, pos, *_) in atual.items():
        antes = anterior.get(ibge, [None, None, None])[2]
        if pos is not None and antes is not None and pos != antes:
            mudancas.append((ibge, antes, pos))
    return mudancas

