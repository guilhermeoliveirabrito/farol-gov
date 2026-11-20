from farol.medalhas import hall_da_fama, podios, semana_de


def _aval(posicoes):
    # nota cai junto com a posicao, e empate de posicao vira empate de nota
    return {ibge: [100.0 - pos, "A", pos] for ibge, pos in posicoes.items()}


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


def test_empate_total_divide_a_medalha_e_o_seguinte_leva_a_proxima():
    # dois empatados em tudo no 1o: os dois levam ouro, o seguinte leva prata (nao some)
    semanas = podios([("2026-11-16", None, _aval({"a": 1, "b": 1, "c": 3, "d": 4}))])
    assert semanas[0]["ouro"] == ["a", "b"]
    assert semanas[0]["prata"] == ["c"]
    assert semanas[0]["bronze"] == ["d"]


def test_mesmo_servidor_desempata_pela_populacao():
    # tres cidades no mesmo servidor tem tudo identico: decide quem protege mais gente
    aval = {"a": [90.0, "A", 1], "b": [90.0, "A", 1], "c": [90.0, "A", 1]}
    snap = _snap({"a": ("pppf", 3), "b": ("pppf", 3), "c": ("pppf", 3)})
    s = podios([("2026-11-17", snap, aval)], populacao={"a": 10_000, "b": 30_000, "c": 20_000})[0]
    assert (s["ouro"], s["prata"], s["bronze"]) == (["b"], ["c"], ["a"])
    assert s["desempate"]["ouro"] == "maior população (mais gente protegida)"


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


def _snap(status):
    return {"m": {ibge: [3, st, extra] for ibge, (st, extra) in status.items()}}


def test_cidade_com_item_nao_verificado_nao_concorre():
    aval = {"a": [100.0, "A", 1], "b": [94.0, "A", 2], "c": [90.0, "A", 3], "d": [80.0, "B", 4]}
    snap = _snap({"a": ("ppep", 0), "b": ("pppp", 0), "c": ("pppw", 0), "d": ("ppwf", 0)})
    s = podios([("2026-11-17", snap, aval)])[0]
    assert (s["ouro"], s["prata"], s["bronze"]) == (["b"], ["c"], ["d"])


def test_desempate_por_detalhes_e_itens_inteiros():
    aval = {"a": [90.0, "A", 1], "b": [90.0, "A", 1], "c": [90.0, "A", 1]}
    # b tem mais pontos de detalhe; a e c empatam nos detalhes e a tem mais itens inteiros
    snap = {"detalhes": 1, "m": {"a": [3, "pppf", 1.0], "b": [3, "pppf", 3.5], "c": [3, "ppww", 1.0]}}
    s = podios([("2026-11-17", snap, aval)])[0]
    assert (s["ouro"], s["prata"], s["bronze"]) == (["b"], ["a"], ["c"])
    assert s["desempate"] == {"ouro": "mais pontos de detalhe", "prata": "mais itens cumpridos por inteiro"}


def test_mesmo_servidor_desempata_pela_populacao_e_nao_pula_ninguem():
    # a, b e c no mesmo servidor com tudo igual: o podio e das tres, pela populacao.
    # d tem nota menor e nao leva nada so por estar em outro servidor
    aval = {"a": [90.0, "A", 1], "b": [90.0, "A", 1], "c": [90.0, "A", 1], "d": [85.0, "B", 4]}
    snap = {"m": {x: [3, "pppp", 0, "", "10.0.0.1"] for x in "abc"} | {"d": [3, "pppw", 0, "", "10.0.0.2"]}}
    s = podios([("2026-11-19", snap, aval)], populacao={"a": 100, "b": 300, "c": 200})[0]
    assert (s["ouro"], s["prata"], s["bronze"]) == (["b"], ["c"], ["a"])
    assert s["desempate"] == {"ouro": "maior população (mais gente protegida)", "prata": "maior população (mais gente protegida)"}


def test_mesmo_servidor_com_nota_diferente_concorre_normal():
    aval = {"a": [90.0, "A", 1], "b": [85.0, "B", 2], "c": [80.0, "B", 3]}
    snap = {"m": {x: [3, "pppp", 0, "", "10.0.0.1"] for x in "abc"}}
    s = podios([("2026-11-19", snap, aval)])[0]
    assert (s["ouro"], s["prata"], s["bronze"]) == (["a"], ["b"], ["c"])
