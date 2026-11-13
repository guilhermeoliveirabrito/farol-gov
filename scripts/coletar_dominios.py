"""
Monta data/dominios.csv com o site oficial de cada município a partir do Wikidata.

Uso:
    python scripts/coletar_dominios.py [-o data/dominios.csv]
"""
import argparse
import json
import sys
import urllib.parse
import urllib.request

from farol import USER_AGENT
from farol.dominios import Entidade, deve_ignorar, normalizar_host, salvar_csv, uf_do_ibge

SPARQL_URL = "https://query.wikidata.org/sparql"

# Q3184121 = município do Brasil, P1585 = código IBGE, P856 = site oficial
QUERY = """
SELECT ?ibge ?nome ?site WHERE {
  ?mun wdt:P31 wd:Q3184121 ;
       wdt:P1585 ?ibge ;
       wdt:P856 ?site .
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


def montar_lista(linhas):
    por_ibge = {}
    for linha in linhas:
        ibge = linha["ibge"]["value"].strip()
        host = normalizar_host(linha["site"]["value"])
        if len(ibge) != 7 or not host or deve_ignorar(host):
            continue
        item = por_ibge.setdefault(ibge, {"nome": linha["nome"]["value"], "sites": []})
        item["sites"].append(host)

    entidades = []
    for ibge, item in sorted(por_ibge.items()):
        entidades.append(Entidade(
            ibge=ibge,
            municipio=item["nome"],
            uf=uf_do_ibge(ibge),
            dominio=escolher_site(item["sites"]),
        ))
    return entidades


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--saida", default="data/dominios.csv")
    args = parser.parse_args()

    print("buscando municipios no wikidata...", file=sys.stderr)
    linhas = buscar_wikidata()
    entidades = montar_lista(linhas)
    salvar_csv(args.saida, entidades)
    print(f"{len(entidades)} municipios com site salvos em {args.saida}", file=sys.stderr)


if __name__ == "__main__":
    main()
