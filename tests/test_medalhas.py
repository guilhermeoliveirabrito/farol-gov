from farol.medalhas import hall_da_fama, podios, semana_de


def _aval(posicoes):
    return {ibge: [90.0, "A", pos] for ibge, pos in posicoes.items()}


def test_semana_comeca_na_segunda():
    assert semana_de("2026-11-16") == "2026-11-16"  # segunda
    assert semana_de("2026-11-17") == "2026-11-16"
    assert semana_de("2026-11-22") == "2026-11-16"  # domingo
    assert semana_de("2026-11-13") == "2026-11-09"


def test_vale_a_ultima_varredura_da_semana():
    tempo = [
        ("2026-11-13", None, _aval({"a": 1, "b": 2, "c": 3})),
        ("2026-11-16", None, _aval({"b": 1, "a": 2, "c": 3})),  # rodada com problema
        ("2026-11-17", None, _aval({"c": 1, "b": 2, "a": 3})),  # refeita no dia seguinte
    ]
    semanas = podios(tempo)
    assert [s["semana"] for s in semanas] == ["2026-11-09", "2026-11-16"]
    assert semanas[1]["data"] == "2026-11-17"
    assert (semanas[1]["ouro"], semanas[1]["prata"], semanas[1]["bronze"]) == (["c"], ["b"], ["a"])
    assert not semanas[0]["parcial"] and semanas[1]["parcial"]


def test_empate_divide_a_medalha_como_nas_olimpiadas():
    # dois empatados em 1o: os dois levam ouro, ninguem leva prata e o seguinte leva bronze
    semanas = podios([("2026-11-16", None, _aval({"a": 1, "b": 1, "c": 3, "d": 4}))])
    assert semanas[0]["ouro"] == ["a", "b"]
    assert semanas[0]["prata"] == []
    assert semanas[0]["bronze"] == ["c"]


def test_hall_da_fama_por_pontos_e_desempate():
    semanas = [
        {"ouro": ["a"], "prata": ["b"], "bronze": ["c"]},
        {"ouro": ["b"], "prata": ["a"], "bronze": ["c"]},
        {"ouro": [], "prata": ["d", "e"], "bronze": ["c"]},
    ]
    hall = hall_da_fama(semanas)
    # a e b: 1 ouro + 1 prata = 15 pontos, empate total -> dividem o 1o lugar
    assert hall[0][0] == "a" and hall[0][5] == 1
    assert hall[1][0] == "b" and hall[1][5] == 1
    # c: 3 bronzes = 7,5; d e e: 1 prata = 5
    assert hall[2] == ["c", 0, 0, 3, 7.5, 3]
    assert [linha[5] for linha in hall[3:]] == [4, 4]


def test_desempate_por_ouro_antes_de_prata():
    # mesmos 10 pontos: 1 ouro ganha de 2 pratas
    hall = hall_da_fama([{"ouro": ["a"], "prata": ["b"], "bronze": []}, {"ouro": [], "prata": ["b"], "bronze": []}])
    assert [linha[0] for linha in hall] == ["a", "b"]
    assert [linha[5] for linha in hall] == [1, 2]
