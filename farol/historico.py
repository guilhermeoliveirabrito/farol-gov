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
from .nota import PESOS, calcular_nota, conceito, excelencia, grau

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
        municipios[r["ibge"]] = [flags, status, excelencia(r.get("checks", {})), graus, r.get("ip") or ""]
    return {
        "data": dia_da_varredura(dados["gerado_em"]),
        "metodologia": dados.get("metodologia", 1),
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
    resultados = [Resultado(c, STATUS[s]) for c, s in zip(checks, status) if s in STATUS]
    # historico antigo nao tem os graus: item cumprido vale o cheio, como era antes
    valores = {c: GRAUS.index(g) / 20 for c, g in zip(checks, graus or "") if g in GRAUS and c in PESOS}
    return calcular_nota(resultados, valores if graus else None)


def posicoes(notas):
    """Posicao no ranking, com empate dividindo a mesma posicao (1, 2, 2, 4...)."""
    ordem = sorted(notas.values(), reverse=True)
    primeira = {}
    for i, n in enumerate(ordem, 1):
        primeira.setdefault(n, i)
    return {ibge: primeira[n] for ibge, n in notas.items()}


def avaliar_snapshot(snap):
    """Devolve {ibge: [nota, conceito, posicao oficial, posicao geral]} com as regras atuais.

    Ranking oficial: so quem teve todos os itens daquela varredura verificados. Item nao
    verificado sai da conta da nota, entao quem teve item sem resposta pode ficar com
    nota maior do que a real; essas cidades entram so no ranking geral.
    """
    checks = snap["checks"]
    geral, oficial, saida = {}, {}, {}
    for ibge, (flags, status, *resto) in snap["m"].items():
        graus = resto[1] if len(resto) > 1 else ""
        nota = nota_do_status(checks, status, graus) if flags & ACESSIVEL else None
        saida[ibge] = [nota, conceito(nota) if nota is not None else None, None, None]
        if nota is not None and flags & ELEGIVEL:
            geral[ibge] = nota
            if "e" not in status:
                oficial[ibge] = nota
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

