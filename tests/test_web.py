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


def test_conteudo_misto():
    from farol.checks.web import avaliar_conteudo_misto
    ok = resp(HTTPS, corpo=b'<html><script src="https://cdn/x.js"></script><a href="http://outro.gov.br">link</a></html>')
    assert avaliar_conteudo_misto(ok).status == PASS

    script = resp(HTTPS, corpo=b'<html><script type="text/javascript" src="http://cdn/x.js"></script></html>')
    assert avaliar_conteudo_misto(script).status == FAIL

    css = resp(HTTPS, corpo=b"<link href='http://x/a.css' rel='stylesheet'>")
    assert avaliar_conteudo_misto(css).status == FAIL

    imagem = resp(HTTPS, corpo=b"<img alt=logo src=http://x/logo.png>")
    assert avaliar_conteudo_misto(imagem).status == WARN

    assert avaliar_conteudo_misto(resp(HTTP, corpo=b"<html>")).status == FAIL
    assert avaliar_conteudo_misto(resp(HTTPS, corpo=b"")).status == ERROR


def test_cookies():
    from farol.checks.web import avaliar_cookies
    assert avaliar_cookies([]).status == PASS
    assert avaliar_cookies(["s=1; Path=/; Secure; HttpOnly; SameSite=Lax"]).status == PASS
    assert avaliar_cookies(["s=1; Secure"]).status == WARN
    # o Expires tem virgula, nao pode confundir o parser
    r = avaliar_cookies(["PHPSESSID=abc; expires=Wed, 21 Oct 2026 07:28:00 GMT; path=/"])
    assert r.status == FAIL
    assert "PHPSESSID" in r.detalhe


def test_certificado_vencendo():
    from farol.checks.web import avaliar_validade
    agora = 1_800_000_000
    assert avaliar_validade(agora + 90 * 86400, agora).status == PASS
    vencendo = avaliar_validade(agora + 5 * 86400, agora)
    assert vencendo.status == WARN
    assert "5 dia" in vencendo.detalhe


def test_tls_antigo_aceito():
    cliente = FakeCliente({
        HTTPS: resp(HTTPS, headers=HEADERS_BONS),
        HTTP: resp(HTTP, status=301, headers={"location": HTTPS}),
    }, tls_antigo="TLSv1.1")
    _, resultados = checar_web(HOST, cliente)
    r = _por_check(resultados)
    assert r["tls_antigo"].status == FAIL
    assert "TLSv1.1" in r["tls_antigo"].detalhe


def test_pagina_inicial_nao_e_baixada_duas_vezes():
    cliente = FakeCliente({
        HTTPS: resp(HTTPS, headers=HEADERS_BONS),
        HTTP: resp(HTTP, status=301, headers={"location": HTTPS}),
        SEC_TXT: resp(SEC_TXT, status=404),
    })
    checar_web(HOST, cliente)
    assert [u for u, _ in cliente.chamadas].count(HTTPS) == 1


def test_cookies_da_primeira_resposta_contam():
    final = "https://www.cidade.sp.gov.br/portal/"
    cliente = FakeCliente({
        HTTPS: resp(HTTPS, status=302, headers={"location": final}, cookies=["sessao=1; path=/"]),
        final: resp(final, headers=HEADERS_BONS),
        HTTP: resp(HTTP, status=301, headers={"location": HTTPS}),
    })
    _, resultados = checar_web(HOST, cliente)
    assert _por_check(resultados)["cookies"].status == FAIL


def test_tls_antigo_servidor_mudo_conta_como_recusa():
    # servidor que aceita o TCP e nunca responde o ClientHello antigo (firewall que descarta)
    import socket
    import threading

    from farol.checks.web import ClienteHTTP

    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen()
    conexoes = []
    threading.Thread(target=lambda: conexoes.append(srv.accept()), daemon=True).start()
    try:
        assert ClienteHTTP(timeout=0.3).aceita_tls_antigo("127.0.0.1", srv.getsockname()[1]) is None
    finally:
        srv.close()


def test_leitura_do_corpo_para_no_prazo():
    import time

    from farol.checks.web import _ler_com_prazo

    class Gotejando:
        # servidor que manda um byte de cada vez, pra sempre
        def read1(self, n):
            time.sleep(0.01)
            return b"x"

    inicio = time.monotonic()
    corpo = _ler_com_prazo(Gotejando(), 512 * 1024, time.monotonic() + 0.1)
    assert time.monotonic() - inicio < 0.3
    assert 0 < len(corpo) < 100


def test_site_fora_do_ar_nao_tenta_a_home_tres_vezes():
    from tests.fakes import FakeCliente

    class Morto(FakeCliente):
        def get(self, url, verificar=True, ler=0):
            self.chamadas.append(url)
            raise ErroConexao("timeout")

    cliente = Morto({})
    acessivel, resultados = checar_web("www.morto.sp.gov.br", cliente)
    assert not acessivel
    assert len(cliente.chamadas) == 2  # uma no https, uma no http
    assert {r.check for r in resultados} >= {"headers", "conteudo_misto", "cookies"}
