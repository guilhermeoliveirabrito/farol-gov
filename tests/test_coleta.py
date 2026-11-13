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
