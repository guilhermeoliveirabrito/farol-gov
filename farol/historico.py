"""Histórico semanal da varredura.

Cada semana vira um arquivo pequeno em data/historico/AAAA-MM-DD.json com só o
necessário pra recalcular nota e posição: o status de cada item, por município.
O json completo (uns 4 MB) fica só no latest.json, pra não inchar o repositório.

A nota de semanas antigas é sempre recalculada com as regras atuais (farol.nota),
assim a série fica comparável. Itens que ainda não existiam numa semana simplesmente
não entram na conta daquela semana.
"""
import json
from pathlib import Path

from .checks import Resultado
from .nota import calcular_nota, conceito

CODIGO = {"pass": "p", "warn": "w", "fail": "f", "error": "e"}
STATUS = {v: k for k, v in CODIGO.items()}

ACESSIVEL = 1
ELEGIVEL = 2  # sem aviso que tira do ranking (dominio fora do .gov.br, repetido...)

AVISOS_FORA = {"fora_do_gov_br", "dominio_compartilhado"}


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
        municipios[r["ibge"]] = [flags, status]
    return {
        "data": dados["gerado_em"][:10],
        "metodologia": dados.get("metodologia", 1),
        "checks": checks,
        "m": municipios,
    }


def salvar(dados, pasta):
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


def nota_do_status(checks, status):
    resultados = [Resultado(c, STATUS[s]) for c, s in zip(checks, status) if s in STATUS]
    return calcular_nota(resultados)


def posicoes(notas):
    """Posicao no ranking, com empate dividindo a mesma posicao (1, 2, 2, 4...)."""
    ordem = sorted(notas.values(), reverse=True)
    primeira = {}
    for i, n in enumerate(ordem, 1):
        primeira.setdefault(n, i)
    return {ibge: primeira[n] for ibge, n in notas.items()}


def avaliar_snapshot(snap):
    """Devolve {ibge: (nota, conceito, posicao ou None)} com as regras atuais."""
    checks = snap["checks"]
    notas, saida = {}, {}
    for ibge, (flags, status) in snap["m"].items():
        nota = nota_do_status(checks, status) if flags & ACESSIVEL else None
        saida[ibge] = [nota, conceito(nota) if nota is not None else None, None]
        if nota is not None and flags & ELEGIVEL:
            notas[ibge] = nota
    for ibge, pos in posicoes(notas).items():
        saida[ibge][2] = pos
    return saida


def resumo_nacional(snap, avaliacao):
    """Uma linha do grafico de evolucao: media, conceitos e adocao de cada item."""
    ranqueados = [i for i, (_, _, pos) in avaliacao.items() if pos is not None]
    n = len(ranqueados)
    if not n:
        return None
    conceitos = {c: 0 for c in "ABCDF"}
    for i in ranqueados:
        conceitos[avaliacao[i][1]] += 1
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
    }


def variacoes(anterior, atual):
    """Quem subiu e quem caiu entre duas semanas: lista de (ibge, pos_antes, pos_agora)."""
    mudancas = []
    for ibge, (_, _, pos) in atual.items():
        antes = anterior.get(ibge, [None, None, None])[2]
        if pos is not None and antes is not None and pos != antes:
            mudancas.append((ibge, antes, pos))
    return mudancas

