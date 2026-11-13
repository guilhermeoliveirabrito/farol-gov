import importlib.util
import json
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parent.parent / "scripts" / "montar_site.py"
spec = importlib.util.spec_from_file_location("montar_site", ARQUIVO)
montar_site = importlib.util.module_from_spec(spec)
spec.loader.exec_module(montar_site)

from farol.nota import PESOS  # noqa: E402


def test_ordem_dos_checks_bate_com_os_pesos():
    # se alguem adicionar um check novo e esquecer daqui, a pagina mostra o status errado
    assert montar_site.CHECKS == list(PESOS)


def _resultado(ibge, uf, status="pass"):
    return {
        "ibge": ibge, "municipio": "Cidade", "uf": uf, "dominio": "www.cidade.gov.br",
        "lat": -8.05, "lon": -34.88, "nota": 90.0, "conceito": "A",
        "acessivel": True, "ranking": True, "avisos": ["dominio_alternativo"],
        "checks": {c: {"status": status, "detalhe": f"detalhe {c}"} for c in PESOS},
    }


def test_resumo_compacto():
    dados = {"gerado_em": "2026-11-13T00:00:00+00:00", "total": 2, "resultados": [
        _resultado("2611606", "PE"),
        _resultado("3550308", "SP", status="warn"),
    ]}
    resumo, por_uf = montar_site.resumir(dados)

    pe = resumo["municipios"][0]
    assert pe[0] == "2611606"
    assert pe[-1] == "p" * 9
    assert pe[-2] == montar_site.ACESSIVEL | montar_site.RANKING
    assert resumo["municipios"][1][-1] == "w" * 9

    assert set(por_uf) == {"PE", "SP"}
    assert por_uf["PE"]["2611606"]["d"][0] == "detalhe https"
    assert por_uf["PE"]["2611606"]["a"] == ["dominio_alternativo"]


def test_montar_pasta(tmp_path):
    (tmp_path / "site").mkdir()
    (tmp_path / "site" / "index.html").write_text("<!doctype html>")
    (tmp_path / "data" / "resultados").mkdir(parents=True)
    (tmp_path / "data" / "resultados" / "latest.json").write_text(json.dumps({
        "gerado_em": "2026-11-13T00:00:00+00:00", "total": 1, "resultados": [_resultado("2611606", "PE")],
    }))
    (tmp_path / "data" / "sem_site.csv").write_text("ibge,municipio,uf,dominio,lat,lon\n5200050,Abadia,GO,,-16.75,-49.44\n")

    saida = tmp_path / "_site"
    montar_site.montar(tmp_path, saida)

    assert (saida / "index.html").exists()
    assert json.loads((saida / "dados" / "resumo.json").read_text())["municipios"][0][0] == "2611606"
    assert "2611606" in json.loads((saida / "dados" / "uf" / "PE.json").read_text())
    assert json.loads((saida / "dados" / "sem_site.json").read_text()) == [["5200050", "Abadia", "GO", -16.75, -49.44]]


def test_manchete_com_dado_da_semana():
    dados = {"gerado_em": "x", "total": 10, "resultados": []}
    for i in range(10):
        r = _resultado(f"26116{i:02d}", "PE")
        # 7 de 10 sem dmarc bloqueando
        if i < 7:
            r["checks"]["dmarc"]["status"] = "warn" if i % 2 else "fail"
        dados["resultados"].append(r)
    resumo, _ = montar_site.resumir(dados)
    assert montar_site.manchete(resumo).startswith("7 em cada 10 prefeituras")


def test_manchete_injetada_no_html(tmp_path):
    (tmp_path / "site").mkdir()
    (tmp_path / "site" / "index.html").write_text(montar_site.PERGUNTA + montar_site.TOTAL, encoding="utf-8")
    (tmp_path / "data" / "resultados").mkdir(parents=True)
    r = _resultado("2611606", "PE", status="fail")
    (tmp_path / "data" / "resultados" / "latest.json").write_text(json.dumps({"gerado_em": "x", "total": 3633, "resultados": [r]}))
    montar_site.montar(tmp_path, tmp_path / "_site")
    html = (tmp_path / "_site" / "index.html").read_text(encoding="utf-8")
    assert "10 em cada 10" in html
    assert ">3.633<" in html
