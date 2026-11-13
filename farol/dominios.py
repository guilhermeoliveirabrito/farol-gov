import csv
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

# dois primeiros digitos do codigo IBGE -> UF
UF_POR_CODIGO = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP",
    "17": "TO", "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB",
    "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
    "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS",
    "51": "MT", "52": "GO", "53": "DF",
}

# sites que aparecem no wikidata mas nao sao o site da prefeitura
IGNORAR = (
    "facebook.com", "instagram.com", "twitter.com", "x.com", "youtube.com",
    "wikipedia.org", "blogspot.com", "wordpress.com", "google.com",
)

CAMPOS = ["ibge", "municipio", "uf", "dominio"]


@dataclass(frozen=True)
class Entidade:
    ibge: str
    municipio: str
    uf: str
    dominio: str


def uf_do_ibge(codigo):
    return UF_POR_CODIGO.get(str(codigo)[:2], "")


def normalizar_host(url):
    """Recebe uma url (ou só o host) e devolve o hostname em minúsculas."""
    url = url.strip()
    if not url:
        return ""
    if "://" not in url:
        url = "http://" + url
    host = urlsplit(url).hostname or ""
    return host.rstrip(".").lower()


def deve_ignorar(host):
    return any(host == d or host.endswith("." + d) for d in IGNORAR)


def dominio_email(host):
    # e-mail normalmente fica no dominio "pelado", sem o www
    if host.startswith("www."):
        return host[4:]
    return host


def alternativo(host):
    """www.x.gov.br <-> x.gov.br. Muita entrada do wikidata so funciona numa das duas formas."""
    return host[4:] if host.startswith("www.") else "www." + host


def fora_do_gov_br(host):
    return not host.endswith(".gov.br")


def ler_csv(caminho):
    with open(caminho, newline="", encoding="utf-8") as f:
        return [Entidade(**{k: linha[k] for k in CAMPOS}) for linha in csv.DictReader(f)]


def salvar_csv(caminho, entidades):
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        for e in entidades:
            w.writerow({"ibge": e.ibge, "municipio": e.municipio, "uf": e.uf, "dominio": e.dominio})
