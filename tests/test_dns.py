import pytest

from farol.checks import ERROR, FAIL, PASS, WARN
from farol.checks.dns import avaliar_dmarc, avaliar_spf, checar_dmarc, checar_dnssec, checar_spf
from tests.fakes import FakeResolver


@pytest.mark.parametrize("registro,esperado", [
    ("v=spf1 include:_spf.google.com -all", PASS),
    ("v=spf1 mx ~all", PASS),
    ("v=spf1 a mx ?all", WARN),
    ("v=spf1 +all", FAIL),
    ("v=spf1 all", FAIL),
    ("v=spf1 a mx", WARN),
    ("V=SPF1 MX -ALL", PASS),
])
def test_spf(registro, esperado):
    assert avaliar_spf([registro]).status == esperado


def test_spf_ignora_outros_txt():
    r = avaliar_spf(["google-site-verification=abc", "v=spf1 -all"])
    assert r.status == PASS


def test_sem_spf():
    assert avaliar_spf(["MS=ms123"]).status == FAIL


def test_dois_registros_spf_e_invalido():
    r = avaliar_spf(["v=spf1 -all", "v=spf1 mx ~all"])
    assert r.status == FAIL
    assert "mais de um" in r.detalhe


def test_spf_segue_redirect():
    resolver = FakeResolver(txt={
        "cidade.sp.gov.br": ["v=spf1 redirect=_spf.provedor.com.br"],
        "_spf.provedor.com.br": ["v=spf1 ip4:10.0.0.0/8 -all"],
    })
    r = checar_spf("cidade.sp.gov.br", resolver)
    assert r.status == PASS
    assert "_spf.provedor.com.br" in r.detalhe


@pytest.mark.parametrize("registro,esperado", [
    ("v=DMARC1; p=reject; rua=mailto:dmarc@exemplo.gov.br", PASS),
    ("v=DMARC1; p=quarantine; pct=100", PASS),
    ("v=DMARC1; p=none", WARN),
    ("v=DMARC1; rua=mailto:x@y.com", FAIL),
    ("v=DMARC1;p=REJECT", PASS),
])
def test_dmarc(registro, esperado):
    assert avaliar_dmarc([registro]).status == esperado


def test_dmarc_consulta_subdominio_certo():
    resolver = FakeResolver(txt={"_dmarc.cidade.rs.gov.br": ["v=DMARC1; p=reject"]})
    assert checar_dmarc("cidade.rs.gov.br", resolver).status == PASS
    assert checar_dmarc("outra.rs.gov.br", resolver).status == FAIL


def test_erro_de_dns_vira_error():
    resolver = FakeResolver(quebrados={"_dmarc.x.gov.br", "x.gov.br"})
    assert checar_dmarc("x.gov.br", resolver).status == ERROR
    assert checar_spf("x.gov.br", resolver).status == ERROR


def test_dnssec():
    resolver = FakeResolver(enderecos={
        "assinado.gov.br": (True, True),
        "sem.gov.br": (True, False),
    })
    assert checar_dnssec("assinado.gov.br", resolver)[1].status == PASS
    assert checar_dnssec("sem.gov.br", resolver)[1].status == FAIL

    existe, r = checar_dnssec("naoexiste.gov.br", resolver)
    assert not existe
    assert r.status == ERROR
