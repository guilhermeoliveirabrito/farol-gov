"""Medalhas da semana e hall da fama.

Regra de cada semana (segunda a domingo, horario de Brasilia): vale a ULTIMA varredura
da semana. Se rodar mais de uma vez (como na semana de 16/11, que teve varredura com
problema e depois a refeita), so a ultima conta, do mesmo jeito que no historico so
vale a ultima varredura do dia.

Ouro, prata e bronze vao pras posicoes 1, 2 e 3 do ranking dessa varredura. Empate
divide a posicao como nas Olimpiadas: dois empatados em 1o levam ouro e o proximo
ja e 3o (bronze), sem prata.

A semana da varredura mais recente fica marcada como em andamento: se rodar de novo
antes de domingo, o podio dela pode mudar.
"""

from datetime import date, timedelta

TIPOS = ("ouro", "prata", "bronze")
PONTOS = {"ouro": 10, "prata": 5, "bronze": 2.5}


def semana_de(data):
    """Segunda-feira da semana de uma data 'AAAA-MM-DD'."""
    try:
        d = date.fromisoformat(data)
    except (TypeError, ValueError):
        return data  # data estranha vira uma semana so dela, sem quebrar o build
    return (d - timedelta(days=d.weekday())).isoformat()


def podios(tempo):
    """tempo: [(data, snapshot, avaliacao)] em ordem de data (a avaliacao traz a posicao).

    Devolve uma lista de semanas, da mais antiga pra mais nova:
    {"semana", "data", "parcial", "ouro": [ibge...], "prata": [...], "bronze": [...]}
    """
    ultima_da_semana = {}
    for data, _, aval in tempo:
        ultima_da_semana[semana_de(data)] = (data, aval)  # em ordem: a ultima sobrescreve

    semanas = []
    for i, semana in enumerate(sorted(ultima_da_semana)):
        data, aval = ultima_da_semana[semana]
        podio = {"semana": semana, "data": data, "parcial": i == len(ultima_da_semana) - 1}
        for pos, tipo in enumerate(TIPOS, 1):
            podio[tipo] = sorted(ibge for ibge, (_, _, p) in aval.items() if p == pos)
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
