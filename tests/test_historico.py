from farol import historico
from farol.nota import PESOS


def _r(ibge, status, acessivel=True, avisos=()):
    return {
        "ibge": ibge, "acessivel": acessivel, "avisos": list(avisos),
        "checks": {c: {"status": status, "detalhe": ""} for c in PESOS},
    }


def test_compactar_e_recalcular():
    dados = {"gerado_em": "2026-11-16T09:00:00+00:00", "resultados": [
        _r("1", "pass"), _r("2", "warn"), _r("3", "fail", acessivel=False), _r("4", "pass", avisos=["fora_do_gov_br"]),
    ]}
    snap = historico.compactar(dados)
    assert snap["data"] == "2026-11-16"
    assert snap["m"]["1"][:4] == [historico.ACESSIVEL | historico.ELEGIVEL, "p" * len(PESOS), 0, "u" * len(PESOS)]

    aval = historico.avaliar_snapshot(snap)
    assert aval["1"] == [100.0, "A", 1, 1]
    assert aval["2"][2] == 2
    assert aval["3"] == [None, None, None, None]
    # tem nota, mas fica fora do ranking
    assert aval["4"][0] == 100.0 and aval["4"][2] is None


def test_semana_antiga_com_menos_itens_ainda_tem_nota():
    snap = {"data": "2026-11-09", "checks": ["https", "dmarc"], "m": {"1": [3, "pp"], "2": [3, "pf"]}}
    aval = historico.avaliar_snapshot(snap)
    assert aval["1"][0] == 100.0
    assert aval["2"][0] == 50.0


def test_empate_divide_a_posicao():
    assert historico.posicoes({"a": 90, "b": 80, "c": 80, "d": 70}) == {"a": 1, "b": 2, "c": 2, "d": 4}


def test_resumo_nacional():
    snap = historico.compactar({"gerado_em": "2026-11-16T00:00:00", "resultados": [_r("1", "pass"), _r("2", "fail")]})
    linha = historico.resumo_nacional(snap, historico.avaliar_snapshot(snap))
    assert linha["n"] == 2
    assert linha["media"] == 50.0
    assert linha["adocao"]["dmarc"] == 50.0
    assert linha["conceitos"]["A"] == 1 and linha["conceitos"]["F"] == 1
    # ibge "1" e "2" nao tem UF valida, entao nao entram na media por estado
    assert linha["ufs"] == {}


def test_media_por_estado():
    dados = {"gerado_em": "2026-11-16T00:00:00", "resultados": [_r("2611606", "pass"), _r("2611700", "fail"), _r("3550308", "pass")]}
    snap = historico.compactar(dados)
    linha = historico.resumo_nacional(snap, historico.avaliar_snapshot(snap))
    assert linha["ufs"] == {"PE": 50.0, "SP": 100.0}


def test_salvar_e_carregar(tmp_path):
    dados = {"gerado_em": "2026-11-16T09:00:00+00:00", "resultados": [_r("1", "pass")]}
    historico.salvar(dados, tmp_path)
    historico.salvar({**dados, "gerado_em": "2026-11-09T09:00:00+00:00"}, tmp_path)
    assert [s["data"] for s in historico.carregar(tmp_path)] == ["2026-11-09", "2026-11-16"]


def test_uma_varredura_por_dia(tmp_path):
    manha = {"gerado_em": "2026-11-16T09:00:00+00:00", "resultados": [_r("1", "fail")]}
    tarde = {"gerado_em": "2026-11-16T18:30:00+00:00", "resultados": [_r("1", "pass")]}
    historico.salvar(manha, tmp_path)
    historico.salvar(tarde, tmp_path)
    snaps = historico.carregar(tmp_path)
    # um arquivo so, com a ultima varredura do dia
    assert len(snaps) == 1
    assert snaps[0]["m"]["1"][1] == "p" * len(PESOS)


def test_dia_no_horario_de_brasilia():
    # 01:30 UTC do dia 17 ainda e 22:30 do dia 16 no Brasil
    assert historico.dia_da_varredura("2026-11-17T01:30:00+00:00") == "2026-11-16"
    assert historico.dia_da_varredura("2026-11-16T15:00:00+00:00") == "2026-11-16"
    assert historico.dia_da_varredura("x") == "x"


def test_item_nao_verificado_tira_do_ranking_oficial_mas_nao_do_geral():
    dados = {"gerado_em": "2026-11-17T09:00:00+00:00", "resultados": [_r("1", "pass"), _r("2", "warn")]}
    # a cidade 1 teve um item sem resposta: nota continua 100 (o item sai da conta)
    dados["resultados"][0]["checks"]["caa"]["status"] = "error"
    aval = historico.avaliar_snapshot(historico.compactar(dados))
    assert aval["1"][0] == 100.0
    assert aval["1"][2] is None and aval["1"][3] == 1  # fora do oficial, 1o no geral
    assert aval["2"][2] == 1 and aval["2"][3] == 2  # a 2 e a primeira do oficial


def test_nota_do_historico_igual_a_da_varredura():
    # o grau de cada item vai pro historico, entao recalcular da a mesma nota da hora
    dados = {"gerado_em": "2026-11-19T09:00:00+00:00", "resultados": [_r("1", "pass")]}
    dados["resultados"][0]["checks"]["tls"]["detalhe"] = "TLSv1.2"
    dados["resultados"][0]["checks"]["dmarc"]["detalhe"] = "p=quarantine"
    from farol.checks import Resultado
    from farol.nota import calcular_nota

    na_hora = calcular_nota([Resultado(c, v["status"], v["detalhe"]) for c, v in dados["resultados"][0]["checks"].items()])
    aval = historico.avaliar_snapshot(historico.compactar(dados))
    assert aval["1"][0] == na_hora < 100
