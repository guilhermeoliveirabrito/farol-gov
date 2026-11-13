from farol.checks import FAIL, PASS, WARN, Resultado
from farol.dominios import Entidade, dominio_email, normalizar_host, uf_do_ibge
from farol.nota import PESOS, calcular_nota, conceito
from farol.resumo import gerar_markdown, linhas_revisao
from farol.scanner import avaliar, varrer
from tests.fakes import FakeCliente, FakeResolver, resp


def test_nota_maxima_e_minima():
    assert calcular_nota([Resultado(c, PASS) for c in PESOS]) == 100.0
    assert calcular_nota([Resultado(c, FAIL) for c in PESOS]) == 0.0


def test_warn_vale_metade():
    # so dmarc (peso 3) em warn, o resto falhou
    resultados = [Resultado(c, FAIL) for c in PESOS if c != "dmarc"] + [Resultado("dmarc", WARN)]
    assert calcular_nota(resultados) == round(100 * 1.5 / sum(PESOS.values()), 1)


def test_conceitos():
    assert conceito(100) == "A"
    assert conceito(90) == "A"
    assert conceito(89.9) == "B"
    assert conceito(55) == "C"
    assert conceito(35) == "D"
    assert conceito(34.9) == "F"


def test_dominios():
    assert normalizar_host("https://WWW.Recife.PE.gov.br/portal/") == "www.recife.pe.gov.br"
    assert normalizar_host("campinas.sp.gov.br") == "campinas.sp.gov.br"
    assert dominio_email("www.recife.pe.gov.br") == "recife.pe.gov.br"
    assert uf_do_ibge("2611606") == "PE"
    assert uf_do_ibge("5300108") == "DF"


def _ambiente():
    host = "www.cidade.sp.gov.br"
    https, http = f"https://{host}/", f"http://{host}/"
    resolver = FakeResolver(
        txt={
            "cidade.sp.gov.br": ["v=spf1 mx -all"],
            "_dmarc.cidade.sp.gov.br": ["v=DMARC1; p=none"],
        },
        enderecos={host: (True, False)},
    )
    cliente = FakeCliente({
        https: resp(https, headers={"x-content-type-options": "nosniff"}),
        http: resp(http, status=301, headers={"location": https}),
    })
    return Entidade("3509502", "Cidade", "SP", host), resolver, cliente


def test_avaliar_dominio():
    ent, resolver, cliente = _ambiente()
    r = avaliar(ent, resolver, cliente)

    assert r["acessivel"]
    assert set(r["checks"]) == set(PESOS)
    assert r["checks"]["dmarc"]["status"] == WARN
    assert r["checks"]["dnssec"]["status"] == FAIL
    assert 0 < r["nota"] < 100


def test_dominio_que_nao_resolve_fica_sem_nota():
    ent = Entidade("3509502", "Cidade", "SP", "fora.sp.gov.br")
    r = avaliar(ent, FakeResolver(), FakeCliente({}))
    assert not r["acessivel"]
    assert r["nota"] is None
    assert set(r["checks"]) == set(PESOS)


def test_varredura_e_resumo():
    ent, resolver, cliente = _ambiente()
    fora = Entidade("2611606", "Outra", "PE", "fora.pe.gov.br")
    dados = varrer([ent, fora], lambda: resolver, cliente, workers=2)

    assert dados["total"] == 2
    md = gerar_markdown(dados)
    assert "| 1 | SP |" in md
    assert "1 não responderam" in md
    # o dominio que nao resolve gera erro em todos os checks web
    assert "| https | 1 | dominio nao resolve |" in md


def test_usa_dominio_sem_www_quando_o_cadastrado_nao_existe():
    host = "cidade.sp.gov.br"
    resolver = FakeResolver(enderecos={host: (True, True)})
    cliente = FakeCliente({f"https://{host}/": resp(f"https://{host}/")})
    r = avaliar(Entidade("3509502", "Cidade", "SP", "www." + host), resolver, cliente)

    assert r["dominio"] == host
    assert r["dominio_wikidata"] == "www." + host
    assert "dominio_alternativo" in r["avisos"]
    assert r["acessivel"]
    assert r["ranking"]


def test_dominio_fora_do_gov_br_sai_do_ranking():
    host = "www.associacao.org.br"
    resolver = FakeResolver(enderecos={host: (True, False)})
    cliente = FakeCliente({f"https://{host}/": resp(f"https://{host}/")})
    r = avaliar(Entidade("1301159", "Careiro", "AM", host), resolver, cliente)

    assert r["acessivel"]
    assert r["nota"] is not None
    assert not r["ranking"]
    assert "fora_do_gov_br" in r["avisos"]


def test_dominio_repetido_vira_compartilhado():
    ent, resolver, cliente = _ambiente()
    outro = Entidade("3509601", "Vizinha", "SP", ent.dominio)
    dados = varrer([ent, outro], lambda: resolver, cliente, workers=2)

    for r in dados["resultados"]:
        assert "dominio_compartilhado" in r["avisos"]
        assert not r["ranking"]


def test_linhas_de_revisao():
    ent, resolver, cliente = _ambiente()
    fora = Entidade("2611606", "Outra", "PE", "fora.pe.gov.br")
    dados = varrer([ent, fora], lambda: resolver, cliente, workers=2)

    revisao = linhas_revisao(dados)
    assert len(revisao) == 1
    assert revisao[0]["ibge"] == "2611606"
    assert "não existe" in revisao[0]["motivo"]


def test_coordenadas_vao_pro_resultado():
    ent, resolver, cliente = _ambiente()
    com_coord = Entidade(ent.ibge, ent.municipio, ent.uf, ent.dominio, lat="-22.9056", lon="-47.0608")
    r = avaliar(com_coord, resolver, cliente)
    assert (r["lat"], r["lon"]) == (-22.9056, -47.0608)

    sem = avaliar(ent, resolver, cliente)
    assert sem["lat"] is None
