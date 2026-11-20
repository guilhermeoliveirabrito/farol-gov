"""Teste ponta a ponta da pagina: monta o site com os dados do repositorio, sobe um
servidor local e abre no Chromium. Fica fora do `pytest` normal porque precisa do
playwright e de um navegador instalado (no CI isso roda num job separado).

    pip install playwright && playwright install chromium
    pytest e2e
"""

import functools
import http.server
import os
import sys
import threading
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import montar_site  # noqa: E402


class SemLog(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def endereco(tmp_path_factory):
    saida = tmp_path_factory.mktemp("site") / "_site"
    montar_site.montar(RAIZ, saida)
    servidor = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(SemLog, directory=str(saida)))
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{servidor.server_address[1]}/"
    servidor.shutdown()


@pytest.fixture(scope="module")
def navegador():
    with sync_api.sync_playwright() as p:
        # local da pra apontar pro chrome do sistema com CHROME=/usr/bin/google-chrome
        b = p.chromium.launch(executable_path=os.environ.get("CHROME") or None)
        yield b
        b.close()


@pytest.fixture
def pagina(navegador, endereco):
    pg = navegador.new_page(viewport={"width": 1280, "height": 900})
    pg.erros = []
    pg.on("pageerror", lambda e: pg.erros.append(str(e)))
    # violacao de CSP e trusted types aparece como erro no console
    pg.on("console", lambda m: pg.erros.append(m.text) if m.type == "error" else None)
    pg.goto(endereco)
    pg.wait_for_selector("#lista .linha")
    yield pg
    pg.close()


def test_carrega_sem_erros(pagina):
    pagina.wait_for_timeout(1500)  # deixa as secoes que carregam depois terminarem
    assert pagina.erros == []
    assert pagina.locator("#lista .linha").count() > 0
    assert pagina.locator("#lista .esqueleto").count() == 0


def test_busca_abre_a_ficha(pagina):
    primeira = pagina.locator("#lista .linha .nome").first.evaluate("n => [...n.childNodes].find((c) => c.nodeType === 3).textContent")
    pagina.fill("#busca", primeira[:5])
    pagina.wait_for_selector("#sugestoes li")
    pagina.keyboard.press("Enter")
    pagina.wait_for_selector("#ficha[open]")
    assert pagina.locator("#ficha-nome").inner_text().strip() != ""
    assert pagina.locator("#ficha .selo-cidade").count() == 1
    pagina.keyboard.press("Escape")
    pagina.wait_for_selector("#ficha:not([open])", state="attached")


def test_filtro_por_estado(pagina):
    uf = pagina.locator("#filtro-uf option").nth(1).get_attribute("value")
    pagina.select_option("#filtro-uf", uf)
    ufs = set(pagina.locator("#lista .linha .uf").all_inner_texts())
    assert ufs == {uf}


def test_link_direto_da_cidade(navegador, endereco, pagina):
    texto = pagina.locator("#lista .linha .dominio").first.inner_text()
    pagina.locator("#lista .linha").first.click()
    pagina.wait_for_selector("#ficha[open]")
    assert "#m-" in pagina.url
    outra = navegador.new_page()
    outra.goto(pagina.url)
    outra.wait_for_selector("#ficha[open]")
    assert texto in outra.locator("#ficha").inner_text()
    outra.close()


def test_medalhas_e_hall_da_fama(pagina):
    pagina.wait_for_selector("#medalhas:not([hidden])")
    assert pagina.locator("#podio .degrau").count() == 3
    assert pagina.locator("#hall li").count() > 0
    # trocar a semana redesenha o podio sem erro
    opcoes = pagina.locator("#semana-podio option")
    if opcoes.count() > 1:
        pagina.select_option("#semana-podio", opcoes.last.get_attribute("value"))
        assert pagina.locator("#podio .degrau").count() == 3
    assert pagina.erros == []


def test_cidade_sem_posicao_vem_depois_do_ranking(pagina):
    # as primeiras linhas tem posicao; quem nao tem fica pro fim
    assert pagina.locator("#lista .linha").first.locator(".pos-lista").inner_text() == "1º"
    assert pagina.locator("#modo-ranking").count() == 0
    assert pagina.erros == []


def test_barra_fixa_aparece_depois_do_mapa(pagina):
    assert "visivel" not in (pagina.get_attribute("#barra", "class") or "")
    pagina.evaluate("scrollTo(0, document.body.scrollHeight / 2)")
    pagina.wait_for_timeout(400)
    assert "visivel" in pagina.get_attribute("#barra", "class")
    pagina.click("#barra-busca")
    assert pagina.evaluate("document.activeElement.id") == "busca"
