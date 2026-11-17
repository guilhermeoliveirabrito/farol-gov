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
    resumo, por_uf, evolucao = montar_site.resumir(dados)
    campo = {c: i for i, c in enumerate(resumo["campos"])}

    pe = resumo["municipios"][0]
    assert pe[0] == "2611606"
    assert pe[campo["status"]] == "p" * len(PESOS)
    assert pe[campo["flags"]] == montar_site.ACESSIVEL | montar_site.RANKING
    assert pe[campo["pos"]] == 1
    assert pe[campo["var"]] is None  # sem semana anterior
    assert resumo["municipios"][1][campo["status"]] == "w" * len(PESOS)
    assert len(evolucao) == 1

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
    resumo, _, _ = montar_site.resumir(dados)
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


def test_variacao_de_posicao_e_historico_da_cidade():
    from farol import historico

    def semana(data, status_recife):
        resultados = [_resultado("2611606", "PE", status=status_recife), _resultado("2611700", "PE", status="warn")]
        return {"gerado_em": f"{data}T09:00:00+00:00", "total": 2, "resultados": resultados}

    # na primeira semana Recife estava atras; na segunda passou a frente
    antiga = historico.compactar(semana("2026-11-09", "fail"))
    atual = semana("2026-11-16", "pass")
    resumo, por_uf, evolucao = montar_site.resumir(atual, [antiga])
    campo = {c: i for i, c in enumerate(resumo["campos"])}
    recife = next(m for m in resumo["municipios"] if m[0] == "2611606")
    outra = next(m for m in resumo["municipios"] if m[0] == "2611700")

    assert recife[campo["pos"]] == 1 and recife[campo["var"]] == 1
    assert outra[campo["pos"]] == 2 and outra[campo["var"]] == -1
    assert resumo["anterior"] == "2026-11-09"
    assert [h[0] for h in por_uf["PE"]["2611606"]["h"]] == ["2026-11-09", "2026-11-16"]
    assert por_uf["PE"]["2611606"]["h"][0][2] == 2
    assert [e["data"] for e in evolucao] == ["2026-11-09", "2026-11-16"]


def test_cache_busting(tmp_path):
    (tmp_path / "site").mkdir()
    (tmp_path / "site" / "index.html").write_text(
        '<meta name="referrer" content="no-referrer"><link rel="preload" href="dados/resumo.json" as="fetch">'
        '<link rel="stylesheet" href="estilo.css"><script src="app.js" defer></script>', encoding="utf-8")
    (tmp_path / "site" / "app.js").write_text("console.log(1)")
    (tmp_path / "site" / "estilo.css").write_text("body{}")
    (tmp_path / "data" / "resultados").mkdir(parents=True)
    (tmp_path / "data" / "resultados" / "latest.json").write_text(json.dumps({"gerado_em": "x", "total": 1, "resultados": [_resultado("2611606", "PE")]}))
    montar_site.montar(tmp_path, tmp_path / "_site")
    html = (tmp_path / "_site" / "index.html").read_text(encoding="utf-8")
    assert '"app.js?v=' in html and '"estilo.css?v=' in html
    assert 'dados/resumo.json?v=' in html
    assert '<meta name="versao-dados"' in html


def test_varredura_nova_no_mesmo_dia_substitui_no_grafico():
    from farol import historico
    manha = {"gerado_em": "2026-11-16T09:00:00+00:00", "total": 1, "resultados": [_resultado("2611606", "PE", status="fail")]}
    tarde = {"gerado_em": "2026-11-16T18:00:00+00:00", "total": 1, "resultados": [_resultado("2611606", "PE")]}
    resumo, por_uf, evolucao = montar_site.resumir(tarde, [historico.compactar(manha)])
    assert [e["data"] for e in evolucao] == ["2026-11-16"]
    assert evolucao[0]["media"] == 100.0
    assert resumo["anterior"] is None
    assert len(por_uf["PE"]["2611606"]["h"]) == 1


def test_selo():
    svg = montar_site.selo_svg(78.4, "B")
    assert "B · 78/100" in svg and 'aria-label="farol-gov: B · 78/100"' in svg
    assert "sem nota" in montar_site.selo_svg(None, None)


def test_selos_gerados_no_build(tmp_path):
    (tmp_path / "site").mkdir()
    (tmp_path / "site" / "index.html").write_text("<!doctype html>")
    (tmp_path / "data" / "resultados").mkdir(parents=True)
    (tmp_path / "data" / "resultados" / "latest.json").write_text(json.dumps({"gerado_em": "x", "total": 1, "resultados": [_resultado("2611606", "PE")]}))
    montar_site.montar(tmp_path, tmp_path / "_site")
    assert "A · 100/100" in (tmp_path / "_site" / "selos" / "2611606.svg").read_text(encoding="utf-8")
