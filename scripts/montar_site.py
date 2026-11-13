"""
Monta a pasta publicada no GitHub Pages a partir de site/ e dos dados da varredura.

O json completo da varredura tem uns 3 MB. A pagina nao precisa de tudo isso pra abrir,
entao aqui ele vira:
  dados/resumo.json   -> uma linha por municipio, so o necessario pra lista, mapa e ranking
  dados/uf/XX.json    -> detalhe de cada check, carregado so quando alguem abre uma cidade
  dados/sem_site.json -> municipios sem site cadastrado (pontos apagados no mapa)
  dados/latest.json   -> o json completo, minificado, pra quem quiser baixar os dados

Uso:
    python scripts/montar_site.py [--saida _site]
"""
import argparse
import csv
import json
import shutil
from collections import defaultdict
from pathlib import Path

# mesma ordem de farol.nota.PESOS; fica duplicado aqui pra o script nao depender do pacote
CHECKS = ["https", "redirect", "tls", "hsts", "headers", "security_txt", "dnssec", "spf", "dmarc"]
CODIGO = {"pass": "p", "warn": "w", "fail": "f", "error": "e"}

ACESSIVEL = 1
RANKING = 2


def compacto(obj, caminho):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))


def resumir(dados):
    """Devolve (resumo, detalhes_por_uf)."""
    linhas = []
    por_uf = defaultdict(dict)
    for r in dados["resultados"]:
        checks = r.get("checks", {})
        status = "".join(CODIGO.get(checks.get(c, {}).get("status"), "e") for c in CHECKS)
        flags = (ACESSIVEL if r.get("acessivel") else 0) | (RANKING if r.get("ranking", r.get("acessivel")) else 0)
        linhas.append([
            r["ibge"], r["municipio"], r["uf"], r["dominio"],
            r.get("lat"), r.get("lon"), r.get("nota"), r.get("conceito"),
            flags, status,
        ])
        por_uf[r["uf"] or "XX"][r["ibge"]] = {
            "d": [checks.get(c, {}).get("detalhe", "") for c in CHECKS],
            "a": r.get("avisos", []),
        }

    resumo = {
        "gerado_em": dados["gerado_em"],
        "total": dados.get("total", len(linhas)),
        "amostra": dados.get("amostra"),
        "checks": CHECKS,
        "campos": ["ibge", "municipio", "uf", "dominio", "lat", "lon", "nota", "conceito", "flags", "status"],
        "municipios": linhas,
    }
    return resumo, por_uf


def sem_site(caminho_csv):
    pontos = []
    with open(caminho_csv, newline="", encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            try:
                lat, lon = round(float(linha["lat"]), 3), round(float(linha["lon"]), 3)
            except (KeyError, ValueError, TypeError):
                continue
            pontos.append([linha["ibge"], linha["municipio"], linha["uf"], lat, lon])
    return pontos


def montar(raiz, saida):
    raiz, saida = Path(raiz), Path(saida)
    if saida.exists():
        shutil.rmtree(saida)
    shutil.copytree(raiz / "site", saida)

    resultados = raiz / "data" / "resultados" / "latest.json"
    if resultados.exists():
        dados = json.loads(resultados.read_text(encoding="utf-8"))
        resumo, por_uf = resumir(dados)
        compacto(resumo, saida / "dados" / "resumo.json")
        for uf, detalhes in por_uf.items():
            compacto(detalhes, saida / "dados" / "uf" / f"{uf}.json")
        compacto(dados, saida / "dados" / "latest.json")
        print(f"{len(resumo['municipios'])} municipios no resumo, {len(por_uf)} arquivos de detalhe")
    else:
        print("sem resultados ainda, a pagina vai mostrar aviso")

    csv_sem_site = raiz / "data" / "sem_site.csv"
    if csv_sem_site.exists():
        pontos = sem_site(csv_sem_site)
        compacto(pontos, saida / "dados" / "sem_site.json")
        print(f"{len(pontos)} municipios sem site")

    revisar = raiz / "data" / "revisar_wikidata.csv"
    if revisar.exists():
        shutil.copy(revisar, saida / "dados" / revisar.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raiz", default=".")
    parser.add_argument("--saida", default="_site")
    args = parser.parse_args()
    montar(args.raiz, args.saida)


if __name__ == "__main__":
    main()
