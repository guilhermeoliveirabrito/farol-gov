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
    assert snap["m"]["1"] == [historico.ACESSIVEL | historico.ELEGIVEL, "p" * len(PESOS)]

    aval = historico.avaliar_snapshot(snap)
    assert aval["1"] == [100.0, "A", 1]
    assert aval["2"][2] == 2
    assert aval["3"] == [None, None, None]
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


def test_salvar_e_carregar(tmp_path):
    dados = {"gerado_em": "2026-11-16T09:00:00+00:00", "resultados": [_r("1", "pass")]}
    historico.salvar(dados, tmp_path)
    historico.salvar({**dados, "gerado_em": "2026-11-09T09:00:00+00:00"}, tmp_path)
    assert [s["data"] for s in historico.carregar(tmp_path)] == ["2026-11-09", "2026-11-16"]
