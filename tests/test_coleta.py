import importlib.util
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parent.parent / "scripts" / "coletar_dominios.py"
spec = importlib.util.spec_from_file_location("coletar_dominios", ARQUIVO)
coleta = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coleta)


def linha(ibge, nome, site=None, coord=None):
    d = {"ibge": {"value": ibge}, "nome": {"value": nome}}
    if site:
        d["site"] = {"value": site}
    if coord:
        d["coord"] = {"value": coord}
    return d


def test_ler_ponto_inverte_lon_lat():
    assert coleta.ler_ponto("Point(-49.4412 -16.7573)") == ("-16.7573", "-49.4412")
    assert coleta.ler_ponto("lixo") == ("", "")


def test_montar_lista_separa_quem_nao_tem_site():
    com, sem = coleta.montar_lista([
        linha("2611606", "Recife", "https://www.recife.pe.gov.br/", "Point(-34.88 -8.05)"),
        linha("2611606", "Recife", "http://recife.com.br"),
        linha("5200050", "Abadia de Goiás", coord="Point(-49.44 -16.75)"),
        linha("3550308", "São Paulo", "https://www.facebook.com/prefsp"),
        linha("123", "codigo invalido", "http://x.gov.br"),
    ])

    assert [e.ibge for e in com] == ["2611606"]
    recife = com[0]
    # prefere o .gov.br quando tem mais de um
    assert recife.dominio == "www.recife.pe.gov.br"
    assert (recife.lat, recife.lon, recife.uf) == ("-8.05", "-34.88", "PE")

    # facebook nao conta como site
    assert {e.ibge for e in sem} == {"5200050", "3550308"}


def test_populacao_fica_com_o_maior_valor():
    linhas = [
        {"ibge": {"value": "2611606"}, "nome": {"value": "Recife"}, "site": {"value": "https://www2.recife.pe.gov.br/"}, "pop": {"value": "1488920"}},
        {"ibge": {"value": "2611606"}, "nome": {"value": "Recife"}, "pop": {"value": "1537704"}},
    ]
    com_site, _ = coleta.montar_lista(linhas)
    assert com_site[0].populacao == "1537704"


def test_slug_e_candidatos():
    assert coleta.slug("Alta Floresta d'Oeste") == "altaflorestadoeste"
    assert coleta.candidatos("Niterói", "RJ")[:2] == ["www.niteroi.rj.gov.br", "niteroi.rj.gov.br"]


def test_sites_suspeitos():
    assert coleta.motivo_suspeito("www.guarulhos.sp.leg.br", "Guarulhos") == "site da câmara municipal (.leg.br)"
    assert coleta.motivo_suspeito("www.camaracg.com.br", "Campina Grande") == "site da câmara municipal"
    # cidade que tem camara no nome nao e confundida
    assert coleta.motivo_suspeito("joaocamara.rn.gov.br", "João Câmara") is None
    assert coleta.motivo_suspeito("www.ceara.com.br", "Varjota") == "portal genérico, não é da prefeitura"
    assert coleta.motivo_suspeito("riotur.rio", "Rio de Janeiro") == "fora do .gov.br"
    assert coleta.motivo_suspeito("www.recife.pe.gov.br", "Recife") is None


def _ent(ibge, nome, uf, dominio=""):
    from farol.dominios import Entidade

    return Entidade(ibge, nome, uf, dominio)


def test_corrigir_troca_suspeito_acha_quem_nao_tinha_e_respeita_o_manual():
    existentes = {"niteroi.rj.gov.br", "www.abadiadegoias.go.gov.br", "www.recife.pe.gov.br"}
    com = [
        _ent("3303302", "Niterói", "RJ", "www.prefeituradeniteroi.org"),
        _ent("2611606", "Recife", "PE", "www.recife.pe.gov.br"),
        _ent("3304557", "Rio de Janeiro", "RJ", "riotur.rio"),
        _ent("1100304", "Vilhena", "RO", "pmvilhena.com.br"),  # suspeito e sem candidato: fica como esta
    ]
    sem = [_ent("5200050", "Abadia de Goiás", "GO"), _ent("5200100", "Abadiânia", "GO")]
    correcoes = {"3304557": {"ibge": "3304557", "dominio": "prefeitura.rio", "motivo": "turismo"}}
    com2, sem2, relatorio = coleta.corrigir(com, sem, lambda h: h in existentes, correcoes, workers=2)

    dominio = {e.ibge: e.dominio for e in com2}
    assert dominio["3303302"] == "niteroi.rj.gov.br"
    assert dominio["2611606"] == "www.recife.pe.gov.br"
    assert dominio["3304557"] == "prefeitura.rio"
    assert dominio["1100304"] == "pmvilhena.com.br"
    assert dominio["5200050"] == "www.abadiadegoias.go.gov.br"
    assert [e.ibge for e in sem2] == ["5200100"]
    origem = {e.ibge: e.origem for e in com2}
    assert origem["3304557"] == "manual" and origem["3303302"] == "inferido" and origem["2611606"] == ""
    assert {r["ibge"] for r in relatorio} == {"3303302", "3304557", "5200050"}
