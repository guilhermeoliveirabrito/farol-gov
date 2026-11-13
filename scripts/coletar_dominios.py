"""
Monta data/dominios.csv com o site oficial de cada município a partir do Wikidata.
Os municípios sem site cadastrado vão para data/sem_site.csv (aparecem em cinza no mapa).

Uso:
    python scripts/coletar_dominios.py [-o data/dominios.csv] [--sem-site data/sem_site.csv]
"""
import argparse
import json
import re
import sys
import urllib.parse
import urllib.request

from farol import USER_AGENT
from farol.dominios import Entidade, deve_ignorar, normalizar_host, salvar_csv, uf_do_ibge

SPARQL_URL = "https://query.wikidata.org/sparql"

# Q3184121 = município do Brasil, P1585 = código IBGE, P856 = site oficial, P625 = coordenadas
QUERY = """
SELECT ?ibge ?nome ?site ?coord WHERE {
  ?mun wdt:P31 wd:Q3184121 ;
       wdt:P1585 ?ibge .
  OPTIONAL { ?mun wdt:P856 ?site . }
  OPTIONAL { ?mun wdt:P625 ?coord . }
  OPTIONAL { ?mun rdfs:label ?pt . FILTER(LANG(?pt) = "pt") }
  OPTIONAL { ?mun rdfs:label ?ptbr . FILTER(LANG(?ptbr) = "pt-br") }
  BIND(COALESCE(?pt, ?ptbr, "") AS ?nome)
}
"""


def buscar_wikidata():
    params = urllib.parse.urlencode({"query": QUERY, "format": "json"})
    req = urllib.request.Request(
        f"{SPARQL_URL}?{params}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        dados = json.load(resp)
    return dados["results"]["bindings"]


def escolher_site(sites):
    # quando tem mais de um site cadastrado, prefere o .gov.br
    sites = sorted(set(sites))
    gov = [s for s in sites if s.endswith(".gov.br")]
    return (gov or sites)[0]


def ler_ponto(wkt):
    """O wikidata manda 'Point(-49.4412 -16.7573)', ou seja, longitude primeiro."""
    m = re.match(r"Point\(\s*(-?[\d.]+)\s+(-?[\d.]+)\s*\)", wkt or "")
    if not m:
        return "", ""
    lon, lat = (round(float(v), 4) for v in m.groups())
    return str(lat), str(lon)


def montar_lista(linhas):
    """Devolve (com_site, sem_site)."""
    por_ibge = {}
    for linha in linhas:
        ibge = linha["ibge"]["value"].strip()
        if len(ibge) != 7:
            continue
        item = por_ibge.setdefault(ibge, {"nome": linha["nome"]["value"], "sites": [], "coord": ("", "")})
        host = normalizar_host(linha.get("site", {}).get("value", ""))
        if host and not deve_ignorar(host):
            item["sites"].append(host)
        if "coord" in linha and not item["coord"][0]:
            item["coord"] = ler_ponto(linha["coord"]["value"])

    com_site, sem_site = [], []
    for ibge, item in sorted(por_ibge.items()):
        lat, lon = item["coord"]
        ent = Entidade(
            ibge=ibge,
            municipio=item["nome"],
            uf=uf_do_ibge(ibge),
            dominio=escolher_site(item["sites"]) if item["sites"] else "",
            lat=lat,
            lon=lon,
        )
        (com_site if ent.dominio else sem_site).append(ent)
    return com_site, sem_site


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--saida", default="data/dominios.csv")
    parser.add_argument("--sem-site", default="data/sem_site.csv")
    args = parser.parse_args()

    print("buscando municipios no wikidata...", file=sys.stderr)
    linhas = buscar_wikidata()
    com_site, sem_site = montar_lista(linhas)
    salvar_csv(args.saida, com_site)
    salvar_csv(args.sem_site, sem_site)
    print(f"{len(com_site)} municipios com site salvos em {args.saida}", file=sys.stderr)
    print(f"{len(sem_site)} sem site cadastrado em {args.sem_site}", file=sys.stderr)


if __name__ == "__main__":
    main()
