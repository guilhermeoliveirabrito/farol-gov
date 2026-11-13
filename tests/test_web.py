from farol.checks import ERROR, FAIL, PASS, WARN
from farol.checks.web import ErroConexao, avaliar_headers, avaliar_hsts, avaliar_security_txt, checar_web
from tests.fakes import FakeCliente, resp

HOST = "www.cidade.sp.gov.br"
HTTPS = f"https://{HOST}/"
HTTP = f"http://{HOST}/"
SEC_TXT = f"https://{HOST}/.well-known/security.txt"

HEADERS_BONS = {
    "strict-transport-security": "max-age=31536000; includeSubDomains",
    "x-content-type-options": "nosniff",
    "x-frame-options": "SAMEORIGIN",
}


def _por_check(resultados):
    return {r.check: r for r in resultados}


def test_hsts():
    assert avaliar_hsts("max-age=63072000; preload").status == PASS
    assert avaliar_hsts('max-age="31536000"').status == PASS
    assert avaliar_hsts("max-age=86400").status == WARN
    assert avaliar_hsts("max-age=0").status == FAIL
    assert avaliar_hsts("").status == FAIL


def test_headers():
    assert avaliar_headers({"x-content-type-options": "nosniff", "x-frame-options": "DENY"}).status == PASS
    assert avaliar_headers({
        "x-content-type-options": "nosniff",
        "content-security-policy": "default-src 'self'; frame-ancestors 'none'",
    }).status == PASS
    assert avaliar_headers({"x-content-type-options": "nosniff, nosniff", "x-frame-options": "DENY"}).status == PASS
    assert avaliar_headers({"x-frame-options": "DENY"}).status == WARN
    assert avaliar_headers({"content-security-policy": "default-src 'self'"}).status == FAIL


def test_security_txt():
    ok = resp(SEC_TXT, headers={"content-type": "text/plain"}, corpo=b"Contact: mailto:seg@cidade.sp.gov.br\n")
    assert avaliar_security_txt(ok).status == PASS

    # site que devolve a home pra qualquer caminho
    html = resp(SEC_TXT, headers={"content-type": "text/html; charset=utf-8"}, corpo=b"<html>contact: x</html>")
    assert avaliar_security_txt(html).status == FAIL

    assert avaliar_security_txt(resp(SEC_TXT, status=404)).status == FAIL


def test_site_bem_configurado():
    cliente = FakeCliente({
        HTTPS: resp(HTTPS, headers=HEADERS_BONS),
        HTTP: resp(HTTP, status=301, headers={"location": HTTPS}),
        SEC_TXT: resp(SEC_TXT, headers={"content-type": "text/plain"}, corpo=b"Contact: mailto:a@b.c"),
    })
    acessivel, resultados = checar_web(HOST, cliente)
    r = _por_check(resultados)

    assert acessivel
    assert all(x.status == PASS for x in resultados), resultados
    assert r["tls"].detalhe == "TLSv1.3"


def test_certificado_invalido():
    cliente = FakeCliente({
        (HTTPS, True): ErroConexao("certificado", "certificate has expired"),
        (HTTPS, False): resp(HTTPS, headers=HEADERS_BONS, tls="TLSv1.2"),
        HTTP: resp(HTTP, status=302, headers={"location": HTTPS}),
    })
    _, resultados = checar_web(HOST, cliente)
    r = _por_check(resultados)

    assert r["https"].status == FAIL
    assert "expired" in r["https"].detalhe
    assert r["tls"].status == PASS
    # navegador ignora HSTS com certificado invalido
    assert r["hsts"].status == FAIL


def test_so_http():
    cliente = FakeCliente({HTTP: resp(HTTP, headers={})})
    acessivel, resultados = checar_web(HOST, cliente)
    r = _por_check(resultados)

    assert acessivel
    assert r["https"].status == FAIL
    assert r["redirect"].status == FAIL
    assert r["tls"].status == FAIL
    assert r["security_txt"].status == FAIL


def test_redirect_em_dois_saltos():
    www = "http://cidade.sp.gov.br/"
    host = "cidade.sp.gov.br"
    cliente = FakeCliente({
        f"https://{host}/": resp(f"https://{host}/", headers=HEADERS_BONS),
        www: resp(www, status=301, headers={"location": "http://www.cidade.sp.gov.br/"}),
        HTTP: resp(HTTP, status=301, headers={"location": "https://www.cidade.sp.gov.br/inicio"}),
    })
    _, resultados = checar_web(host, cliente)
    assert _por_check(resultados)["redirect"].status == PASS


def test_porta_80_fechada_nao_penaliza():
    cliente = FakeCliente({
        HTTPS: resp(HTTPS, headers=HEADERS_BONS),
        HTTP: ErroConexao("timeout"),
    })
    _, resultados = checar_web(HOST, cliente)
    assert _por_check(resultados)["redirect"].status == PASS


def test_tls_antigo():
    cliente = FakeCliente({
        HTTPS: ErroConexao("tls", "UNSUPPORTED_PROTOCOL"),
        HTTP: resp(HTTP),
    })
    _, resultados = checar_web(HOST, cliente)
    r = _por_check(resultados)
    assert r["https"].status == FAIL
    assert r["tls"].status == FAIL


def test_timeout_vira_error():
    cliente = FakeCliente({HTTPS: ErroConexao("timeout"), HTTP: ErroConexao("timeout")})
    acessivel, resultados = checar_web(HOST, cliente)
    r = _por_check(resultados)
    assert not acessivel
    assert r["https"].status == ERROR
    assert r["tls"].status == ERROR
