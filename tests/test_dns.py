import pytest

from farol.checks import ERROR, FAIL, PASS, WARN
from farol.checks.dns import avaliar_dmarc, avaliar_spf, checar_caa, checar_dmarc, checar_dnssec, checar_spf
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

    existe, r, ips = checar_dnssec("naoexiste.gov.br", resolver)
    assert not existe
    assert r.status == ERROR
    assert ips == []


def test_caa_no_proprio_dominio():
    resolver = FakeResolver(caa={"cidade.sp.gov.br": ['0 issue "letsencrypt.org"']})
    r = checar_caa("cidade.sp.gov.br", resolver)
    assert r.status == PASS
    assert "herdado" not in r.detalhe


def test_caa_herdado_do_estado():
    resolver = FakeResolver(caa={"sp.gov.br": ['0 issue "digicert.com"', '0 iodef "mailto:x@sp.gov.br"']})
    r = checar_caa("cidade.sp.gov.br", resolver)
    assert r.status == PASS
    assert "herdado de sp.gov.br" in r.detalhe
    # iodef sozinho nao restringe emissao
    assert r.detalhe.startswith("1 registro")


def test_caa_ausente_e_nao_olha_o_tld():
    resolver = FakeResolver(caa={"br": ['0 issue "x"']})
    assert checar_caa("cidade.sp.gov.br", resolver).status == FAIL


def test_caa_com_erro_de_dns():
    resolver = FakeResolver(quebrados={"cidade.sp.gov.br"})
    assert checar_caa("cidade.sp.gov.br", resolver).status == ERROR


class _Registro:
    def __init__(self, texto):
        self.strings = [texto.encode()]
        self.texto = texto

    def to_text(self):
        return self.texto


class _Resposta:
    def __init__(self, registros, ad=False):
        import dns.flags

        self.rrset = [_Registro(r) for r in registros]
        self.response = type("R", (), {"flags": dns.flags.AD if ad else 0})()


class _Fora:
    def resolve(self, nome, tipo, raise_on_no_answer=False):
        import dns.resolver

        raise dns.resolver.LifetimeTimeout(timeout=6.0, errors={})


class _Responde:
    def __init__(self, dados):
        self.dados = dados

    def resolve(self, nome, tipo, raise_on_no_answer=False):
        return _Resposta(self.dados.get((nome, tipo), []))


def _resolver(publico, reserva):
    from farol.checks.dns import ResolverDNS

    r = ResolverDNS(reserva=False, tentativas=1)
    r._r, r._reserva = publico, reserva
    return r


def test_resolver_do_sistema_cobre_quando_os_publicos_nao_respondem():
    pytest.importorskip("dns.resolver")
    r = _resolver(_Fora(), _Responde({("cidade.sp.gov.br", "TXT"): ["v=spf1 -all"]}))
    assert r.txt("cidade.sp.gov.br") == ["v=spf1 -all"]


def test_txt_vai_primeiro_pro_resolver_do_sistema_e_cai_pro_publico():
    pytest.importorskip("dns.resolver")
    # sistema responde: nem chega nos publicos
    r = _resolver(_Fora(), _Responde({("cidade.sp.gov.br", "TXT"): ["v=spf1 -all"]}))
    assert r._resolve("cidade.sp.gov.br", "TXT")[1] is False
    # sistema fora: usa os publicos
    r = _resolver(_Responde({("cidade.sp.gov.br", "TXT"): ["v=spf1 ~all"]}), _Fora())
    assert r.txt("cidade.sp.gov.br") == ["v=spf1 ~all"]


def test_sem_os_publicos_o_dnssec_fica_nao_verificado_mas_o_site_segue():
    pytest.importorskip("dns.resolver")
    r = _resolver(_Fora(), _Responde({("www.cidade.sp.gov.br", "A"): ["10.0.0.1"]}))
    existe, resultado, ips = checar_dnssec("www.cidade.sp.gov.br", r)
    assert existe and ips == ["10.0.0.1"]
    assert resultado.status == "error" and resultado.detalhe.startswith("LifetimeTimeout")


def test_publico_respondendo_usa_a_flag_ad():
    pytest.importorskip("dns.resolver")
    r = _resolver(_Responde({}), None)
    r._r.resolve = lambda nome, tipo, raise_on_no_answer=False: _Resposta(["10.0.0.1"], ad=True)
    assert r.endereco("www.cidade.sp.gov.br") == (True, True, ["10.0.0.1"])


def test_caa_sem_resposta_com_a_zona_funcionando_conta_como_sem_caa():
    pytest.importorskip("dns.resolver")
    r = _resolver(_Fora(), _Fora())
    assert checar_caa("cidade.sp.gov.br", r, zona_responde=True).status == "fail"
    assert checar_caa("cidade.sp.gov.br", r).status == "error"


def test_email_tls():
    from farol.checks.dns import avaliar_email_tls

    assert avaliar_email_tls(["v=STSv1; id=2024"], ["v=TLSRPTv1; rua=mailto:x"]).detalhe == "MTA-STS e TLS-RPT"
    assert avaliar_email_tls(["v=STSv1; id=2024"], []).detalhe == "MTA-STS, sem TLS-RPT"
    assert avaliar_email_tls([], ["v=TLSRPTv1; rua=mailto:x"]).status == WARN
    assert avaliar_email_tls([], []).status == FAIL


def test_dmarc_com_pct_menor_que_100():
    r = avaliar_dmarc(["v=DMARC1; p=reject; pct=50; rua=mailto:x@y"])
    assert r.status == PASS and r.detalhe == "p=reject; com relatorios; pct=50"
