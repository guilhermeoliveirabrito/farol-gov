"""Medalhas da semana e hall da fama.

Regra de cada semana (segunda a domingo, horario de Brasilia): vale a ULTIMA varredura
da semana. Se rodar mais de uma vez (como na semana de 16/11, que teve varredura com
problema e depois a refeita), so a ultima conta, do mesmo jeito que no historico so
vale a ultima varredura do dia.

Ouro, prata e bronze vao pros 1o, 2o e 3o do ranking dessa varredura (so quem teve todos
os itens verificados). O ranking ja desempata nota igual (historico.chave): itens
cumpridos por inteiro, pontos de excelencia e populacao. Se mesmo assim duas cidades
empatarem em tudo, dividem a medalha e a seguinte leva a proxima.

A semana da varredura mais recente fica marcada como em andamento: se rodar de novo
antes de domingo, o podio dela pode mudar.
"""

from datetime import date, timedelta

from .historico import chave, criterio_do_desempate, detalhes_do_snapshot, posicoes

TIPOS = ("ouro", "prata", "bronze")
PONTOS = {"ouro": 10, "prata": 5, "bronze": 2.5}


def semana_de(data):
    """Segunda-feira da semana de uma data 'AAAA-MM-DD'."""
    try:
        d = date.fromisoformat(data)
    except (TypeError, ValueError):
        return data  # data estranha vira uma semana so dela, sem quebrar o build
    return (d - timedelta(days=d.weekday())).isoformat()


RANKINGS = ("oficial", "geral")


def _chaves(snap, aval, ranking="oficial", populacao=None):
    """{ibge: chave do ranking} de quem concorre: tem posicao e, no oficial, nenhum item sem verificar."""
    chaves = {}
    for ibge, linha in aval.items():
        pos = linha[2] if ranking == "oficial" else (linha[3] if len(linha) > 3 else linha[2])
        if pos is None:
            continue
        m = snap["m"].get(ibge, [0, ""]) if snap else [0, ""]
        status = str(m[1]) if len(m) > 1 else ""
        if ranking == "oficial" and "e" in status:
            continue
        chaves[ibge] = chave(linha[0], status, detalhes_do_snapshot(snap or {}, m), (populacao or {}).get(ibge))
    return chaves


def podios(tempo, ranking="oficial", populacao=None):
    """tempo: [(data, snapshot, avaliacao)] em ordem de data.

    Devolve uma lista de semanas, da mais antiga pra mais nova:
    {"semana", "data", "parcial", "ouro": [ibge...], "prata": [...], "bronze": [...],
     "desempate": {tipo: criterio}, "ordem": [ibge...]}
    """
    ultima_da_semana = {}
    for data, snap, aval in tempo:
        ultima_da_semana[semana_de(data)] = (data, snap, aval)  # em ordem: a ultima sobrescreve

    semanas = []
    ordem_semanas = sorted(ultima_da_semana)
    for i, semana in enumerate(ordem_semanas):
        data, snap, aval = ultima_da_semana[semana]
        chaves = _chaves(snap, aval, ranking, populacao)
        pos = posicoes(chaves)
        ordem = sorted(chaves, key=lambda x: (pos[x], x))
        podio = {"semana": semana, "data": data, "parcial": i == len(ordem_semanas) - 1, "desempate": {}, "ordem": ordem}
        # medalha por posicao distinta: empate total divide a medalha e a seguinte leva a proxima
        niveis = sorted(set(pos.values()))
        for n, tipo in enumerate(TIPOS):
            podio[tipo] = sorted(x for x in chaves if n < len(niveis) and pos[x] == niveis[n])
        # o que separou cada medalha da cidade seguinte, quando a nota era a mesma
        for n, tipo in enumerate(TIPOS):
            if not podio[tipo] or n + 1 >= len(niveis):
                continue
            a = chaves[podio[tipo][0]]
            b = chaves[next(x for x in ordem if pos[x] == niveis[n + 1])]
            criterio = criterio_do_desempate(a, b)
            if criterio:
                podio["desempate"][tipo] = criterio
        semanas.append(podio)
    return semanas


def hall_da_fama(semanas):
    """[[ibge, ouro, prata, bronze, pontos, posicao], ...] do maior campeao pro menor.

    Ordem: pontos (ouro 10, prata 5, bronze 2,5), depois mais ouros, depois mais pratas.
    Se tudo empatar, divide a posicao.
    """
    contagem = {}
    for s in semanas:
        for tipo in TIPOS:
            for ibge in s[tipo]:
                contagem.setdefault(ibge, dict.fromkeys(TIPOS, 0))[tipo] += 1

    linhas = []
    for ibge, c in contagem.items():
        pontos = sum(PONTOS[t] * c[t] for t in TIPOS)
        linhas.append([ibge, c["ouro"], c["prata"], c["bronze"], pontos])
    chave = lambda linha: (-linha[4], -linha[1], -linha[2])  # noqa: E731
    linhas.sort(key=lambda linha: (chave(linha), linha[0]))

    anterior, posicao = None, 0
    for i, linha in enumerate(linhas, 1):
        if chave(linha) != anterior:
            posicao, anterior = i, chave(linha)
        linha.append(posicao)
    return linhas
