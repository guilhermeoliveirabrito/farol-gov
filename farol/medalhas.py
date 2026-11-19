"""Medalhas da semana e hall da fama.

Regra de cada semana (segunda a domingo, horario de Brasilia): vale a ULTIMA varredura
da semana. Se rodar mais de uma vez (como na semana de 16/11, que teve varredura com
problema e depois a refeita), so a ultima conta, do mesmo jeito que no historico so
vale a ultima varredura do dia.

Sao duas premiacoes, uma pra cada ranking: a oficial (so quem teve todos os itens
verificados) e a geral (todo mundo com nota). Ouro, prata e bronze vao pras posicoes
1, 2 e 3 dessa varredura em cada uma. Nota igual desempata
por: mais itens cumpridos por inteiro, mais pontos de excelencia (nota.EXCELENCIA),
melhor media nas 4 semanas anteriores e, por ultimo, maior populacao. Se ainda assim
empatar, divide a medalha, e o seguinte leva a proxima (dois ouros e uma prata).

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


# o que desempata quem tem a mesma nota, nessa ordem
CRITERIOS = (
    "nota",
    "mais itens cumpridos por inteiro",
    "mais pontos de excelência",
    "melhor média nas semanas anteriores",
    "maior população (mais gente protegida)",
)
SEMANAS_DE_CONSTANCIA = 4


RANKINGS = ("oficial", "geral")


def _chaves(snap, aval, anteriores, ranking="oficial", populacao=None):
    """{ibge: (nota, itens inteiros, excelencia, media anterior, populacao)} de quem esta no ranking."""
    chaves = {}
    for ibge, linha in aval.items():
        nota = linha[0]
        # oficial: so quem teve todos os itens verificados (item nao verificado sai da conta
        # da nota, e uma cidade com 3 itens sem resposta podia chegar a 100). geral: todo mundo com nota
        pos = linha[2] if ranking == "oficial" else (linha[3] if len(linha) > 3 else linha[2])
        if pos is None:
            continue
        flags_status = snap["m"].get(ibge, [0, ""]) if snap else [0, ""]
        if ranking == "oficial" and "e" in str(flags_status[1]):
            continue
        inteiros = str(flags_status[1]).count("p")
        extra = flags_status[2] if len(flags_status) > 2 and isinstance(flags_status[2], (int, float)) else 0
        notas = [a[ibge][0] for a in anteriores if a.get(ibge) and a[ibge][0] is not None]
        constancia = round(sum(notas) / len(notas), 2) if notas else 0.0
        chaves[ibge] = (nota, inteiros, extra, constancia, (populacao or {}).get(ibge, 0))
    return chaves


def _classificar(chaves):
    """Posicao densa (1, 1, 2, 3...) pela tupla inteira de criterios.

    Densa e nao olimpica: se dois empatam em tudo no ouro, o seguinte leva prata.
    Com a olimpica (1, 1, 3) um empate no topo sumia com a prata e o bronze, e como
    cidades no mesmo servidor tem a configuracao identica, o podio virava so ouro.
    """
    ordem = sorted(chaves, key=lambda i: chaves[i], reverse=True)
    pos, anterior, saida = 0, None, {}
    for ibge in ordem:
        if chaves[ibge] != anterior:
            pos, anterior = pos + 1, chaves[ibge]
        saida[ibge] = pos
    return saida, ordem


def podios(tempo, ranking="oficial", populacao=None):
    """tempo: [(data, snapshot, avaliacao)] em ordem de data.

    Devolve uma lista de semanas, da mais antiga pra mais nova:
    {"semana", "data", "parcial", "ouro": [ibge...], "prata": [...], "bronze": [...],
     "desempate": {tipo: criterio}} (so quando a medalha foi decidida no desempate)
    """
    ultima_da_semana = {}
    for data, snap, aval in tempo:
        ultima_da_semana[semana_de(data)] = (data, snap, aval)  # em ordem: a ultima sobrescreve

    semanas, finais = [], []
    ordem_semanas = sorted(ultima_da_semana)
    for i, semana in enumerate(ordem_semanas):
        data, snap, aval = ultima_da_semana[semana]
        chaves = _chaves(snap, aval, finais[-SEMANAS_DE_CONSTANCIA:], ranking, populacao)
        posicoes, ordem = _classificar(chaves)
        podio = {"semana": semana, "data": data, "parcial": i == len(ordem_semanas) - 1, "desempate": {}, "ordem": ordem}
        for p, tipo in enumerate(TIPOS, 1):
            podio[tipo] = sorted(ibge for ibge, pos in posicoes.items() if pos == p)
            if podio[tipo]:
                # quem veio logo depois: se tinha a mesma nota, conta qual criterio separou
                seguinte = next((x for x in ordem if posicoes[x] > p), None)
                if seguinte is not None:
                    a, b = chaves[podio[tipo][0]], chaves[seguinte]
                    if a[0] == b[0]:
                        podio["desempate"][tipo] = next(CRITERIOS[k] for k in range(1, len(a)) if a[k] != b[k])
        semanas.append(podio)
        finais.append(aval)
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
