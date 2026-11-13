from farol.checks import FAIL, PASS, WARN, Resultado
from farol.dominios import Entidade, dominio_email, normalizar_host, uf_do_ibge
from farol.nota import PESOS, calcular_nota, conceito
from farol.resumo import gerar_markdown
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
