"""
Monta data/dominios.csv com o site oficial de cada município a partir do Wikidata.
Os municípios sem site cadastrado vão para data/sem_site.csv (aparecem em cinza no mapa).

O Wikidata erra bastante: site de turismo (riotur.rio no Rio de Janeiro), da câmara
(guarulhos.sp.leg.br), portal de notícias, domínio que nem existe mais. Então, depois de
ler o Wikidata, o script:

1. aplica as correções manuais de data/correcoes.csv;
2. quando o site do Wikidata é suspeito (fora do .gov.br, da câmara) ou não existe no
   DNS, ou quando o Wikidata não tem site, procura o padrão oficial
   <nome>.<uf>.gov.br (e variações com www, pm, prefeitura) e usa o primeiro que existir.
   Domínio .gov.br só é registrado por órgão público, então isso é bem seguro.

Tudo que foi trocado fica em data/dominios_corrigidos.csv, com o motivo.

Uso:
    python scripts/coletar_dominios.py [-o data/dominios.csv] [--sem-site data/sem_site.csv]
"""
import argparse
import csv
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

from farol import USER_AGENT
from farol.dominios import Entidade, deve_ignorar, normalizar_host, salvar_csv, uf_do_ibge

SPARQL_URL = "https://query.wikidata.org/sparql"

# Q3184121 = município do Brasil, P1585 = código IBGE, P856 = site oficial, P625 = coordenadas,
# P1082 = população (wdt traz so o valor preferido, que costuma ser o do ultimo censo)
QUERY = """
SELECT ?ibge ?nome ?site ?coord ?pop WHERE {
  ?mun wdt:P31 wd:Q3184121 ;
       wdt:P1585 ?ibge .
  OPTIONAL { ?mun wdt:P856 ?site . }
  OPTIONAL { ?mun wdt:P625 ?coord . }
  OPTIONAL { ?mun wdt:P1082 ?pop . }
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
        item = por_ibge.setdefault(ibge, {"nome": linha["nome"]["value"], "sites": [], "coord": ("", ""), "pop": 0})
        host = normalizar_host(linha.get("site", {}).get("value", ""))
        if host and not deve_ignorar(host):
            item["sites"].append(host)
        if "coord" in linha and not item["coord"][0]:
            item["coord"] = ler_ponto(linha["coord"]["value"])
        try:
            item["pop"] = max(item["pop"], int(float(linha.get("pop", {}).get("value", 0))))
        except ValueError:
            pass

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
            populacao=str(item["pop"]) if item["pop"] else "",
        )
        (com_site if ent.dominio else sem_site).append(ent)
    return com_site, sem_site


# hosts que aparecem no wikidata mas sao portais genericos, nao da prefeitura
GENERICOS = ("ceara.com.br", "bb.com.br", "uol.com.br", "tripod.com", "hpg.ig.com.br", "municipioonline.com.br", "cnm.org.br", "aam.org.br", "amac-acre.com.br")


def slug(nome):
    """'Alta Floresta d'Oeste' -> 'altaflorestadoeste' (como os dominios .gov.br costumam ser)."""
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", sem_acento.lower())


def candidatos(nome, uf):
    base, uf = slug(nome), uf.lower()
    if not base or not uf:
        return []
    return [f"{base}.{uf}.gov.br", f"www.{base}.{uf}.gov.br", f"pm{base}.{uf}.gov.br", f"prefeitura{base}.{uf}.gov.br"]


def motivo_suspeito(host, nome):
    """Por que o site do wikidata parece nao ser o da prefeitura (ou None se parece certo)."""
    if host.endswith(".leg.br"):
        return "site da câmara municipal (.leg.br)"
    primeiro = host.removeprefix("www.").split(".")[0]
    if primeiro.startswith("camara") and "camara" not in slug(nome):
        return "site da câmara municipal"
    if any(host == g or host.endswith("." + g) for g in GENERICOS):
        return "portal genérico, não é da prefeitura"
    if not host.endswith(".gov.br"):
        return "fora do .gov.br"
    return None


def ler_correcoes(caminho):
    """data/correcoes.csv: ibge,dominio,motivo (revisado a mao, vale mais que tudo)."""
    caminho = Path(caminho)
    if not caminho.exists():
        return {}
    with caminho.open(encoding="utf-8", newline="") as f:
        return {linha["ibge"].strip(): linha for linha in csv.DictReader(f) if linha.get("ibge")}


def corrigir(com_site, sem_site, existe, correcoes=None, workers=32):
    """Devolve (com_site, sem_site, relatorio). `existe(host)` diz se o host tem endereco no DNS."""
    correcoes = correcoes or {}
    todos = [(e, True) for e in com_site] + [(e, False) for e in sem_site]

    # primeiro descobre quem precisa de candidato, depois testa tudo em paralelo
    def analisar(par):
        ent, tinha_site = par
        if ent.ibge in correcoes:
            c = correcoes[ent.ibge]
            return replace(ent, dominio=c["dominio"].strip(), origem="manual"), f"correção manual: {c.get('motivo', '').strip()}"
        motivo = None
        if not tinha_site:
            motivo = "sem site no Wikidata"
        else:
            motivo = motivo_suspeito(ent.dominio, ent.municipio)
            if motivo is None and not existe(ent.dominio):
                motivo = "domínio do Wikidata não existe no DNS"
        if motivo is None:
            return ent, None
        for host in candidatos(ent.municipio, ent.uf):
            if host != ent.dominio and existe(host):
                return replace(ent, dominio=host, origem="inferido"), motivo
        return ent, None

    with ThreadPoolExecutor(max_workers=workers) as pool:
        resultados = list(pool.map(analisar, todos))

    novos_com, novos_sem, relatorio = [], [], []
    for (antes, tinha_site), (depois, motivo) in zip(todos, resultados, strict=True):
        if motivo and depois.dominio:
            relatorio.append({
                "ibge": antes.ibge, "municipio": antes.municipio, "uf": antes.uf,
                "dominio_wikidata": antes.dominio if tinha_site else "", "dominio_usado": depois.dominio, "motivo": motivo,
            })
        (novos_com if depois.dominio else novos_sem).append(depois)
    return novos_com, novos_sem, relatorio


def existe_no_dns():
    """Funcao existe(host) com cache; cada thread usa o seu resolver."""
    import threading

    from farol.checks.dns import ErroDNS, ResolverDNS

    local, cache = threading.local(), {}

    def existe(host):
        if host not in cache:
            if not hasattr(local, "r"):
                local.r = ResolverDNS(timeout=5.0, tentativas=1)
            try:
                cache[host] = local.r.endereco(host)[0]
            except ErroDNS:
                cache[host] = False
        return cache[host]

    return existe


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--saida", default="data/dominios.csv")
    parser.add_argument("--sem-site", default="data/sem_site.csv")
    parser.add_argument("--correcoes", default="data/correcoes.csv")
    parser.add_argument("--relatorio", default="data/dominios_corrigidos.csv")
    parser.add_argument("--sem-correcao", action="store_true", help="usa o wikidata do jeito que vier")
    args = parser.parse_args()

    print("buscando municipios no wikidata...", file=sys.stderr)
    linhas = buscar_wikidata()
    com_site, sem_site = montar_lista(linhas)
    if not args.sem_correcao:
        print("conferindo os sites no dns...", file=sys.stderr)
        com_site, sem_site, relatorio = corrigir(com_site, sem_site, existe_no_dns(), ler_correcoes(args.correcoes))
        campos = ["ibge", "municipio", "uf", "dominio_wikidata", "dominio_usado", "motivo"]
        with open(args.relatorio, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=campos)
            w.writeheader()
            w.writerows(sorted(relatorio, key=lambda r: r["ibge"]))
        print(f"{len(relatorio)} sites corrigidos ou encontrados fora do wikidata ({args.relatorio})", file=sys.stderr)
    salvar_csv(args.saida, com_site)
    salvar_csv(args.sem_site, sem_site)
    print(f"{len(com_site)} municipios com site salvos em {args.saida}", file=sys.stderr)
    print(f"{len(sem_site)} sem site cadastrado em {args.sem_site}", file=sys.stderr)


if __name__ == "__main__":
    main()
