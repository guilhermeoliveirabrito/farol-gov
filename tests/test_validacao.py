from farol.validacao import validar


def _r(ibge, acessivel=True, avisos=()):
    return {"ibge": ibge, "acessivel": acessivel, "avisos": list(avisos), "checks": {}}


def _snapshot(data, n, acessiveis):
    return {"data": data, "checks": [], "m": {str(i): [1 if i < acessiveis else 0, ""] for i in range(n)}}


def test_semana_normal_passa():
    dados = {"gerado_em": "2026-11-23T09:00:00+00:00", "resultados": [_r(str(i)) for i in range(100)]}
    problemas, _ = validar(dados, [_snapshot("2026-11-16", 100, 97)])
    assert problemas == []


def test_muitos_sites_sem_resposta_nao_publica():
    # runner bloqueado: metade dos sites "caiu" de uma semana pra outra
    dados = {"gerado_em": "2026-11-23T09:00:00+00:00", "resultados": [_r(str(i), acessivel=i < 50) for i in range(100)]}
    problemas, _ = validar(dados, [_snapshot("2026-11-16", 100, 95)])
    assert any("responderam" in p for p in problemas)


def test_muita_verificacao_incompleta_nao_publica():
    resultados = [_r(str(i), avisos=["verificacao_incompleta"] if i < 20 else []) for i in range(100)]
    problemas, _ = validar({"gerado_em": "2026-11-23T09:00:00+00:00", "resultados": resultados}, [])
    assert any("incompleta" in p for p in problemas)


def test_prazo_estourado_nao_publica():
    dados = {"gerado_em": "2026-11-23T09:00:00+00:00", "sem_visita_por_prazo": 30, "resultados": [_r(str(i)) for i in range(100)]}
    problemas, _ = validar(dados, [])
    assert any("prazo" in p for p in problemas)


def test_compara_com_a_anterior_e_nao_com_o_mesmo_dia():
    # rodar de novo no mesmo dia compara com o dia anterior, nao com o arquivo que vai ser substituido
    dados = {"gerado_em": "2026-11-23T09:00:00+00:00", "resultados": [_r(str(i)) for i in range(100)]}
    _, linhas = validar(dados, [_snapshot("2026-11-16", 100, 97), _snapshot("2026-11-23", 100, 10)])
    assert any("2026-11-16" in linha for linha in linhas)
