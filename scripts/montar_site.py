"""
Monta a pasta publicada no GitHub Pages a partir de site/ e dos dados da varredura.

O json completo da varredura tem uns 4 MB. A pagina nao precisa de tudo isso pra abrir,
entao aqui ele vira:
  dados/resumo.json     -> uma linha por municipio: lista, mapa, ranking e variacao de posicao
  dados/uf/XX.json      -> detalhe de cada check e historico da cidade, carregado so quando alguem abre uma
  dados/historico.json  -> uma linha por semana pro grafico de evolucao
  dados/sem_site.json   -> municipios sem site cadastrado (pontos apagados no mapa)
  dados/latest.json     -> o json completo, minificado, pra quem quiser baixar os dados

Nota, conceito e posicao sao recalculados aqui com as regras atuais (farol.nota), inclusive
pras semanas antigas, pra que a comparacao entre semanas faca sentido.

Uso:
    python scripts/montar_site.py [--saida _site]
"""
import argparse
import csv
import hashlib
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

# roda direto do repositorio, sem precisar de pip install
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from farol import historico, medalhas  # noqa: E402
from farol.dominios import ler_csv  # noqa: E402
from farol.nota import PESOS, criterios_de_excelencia  # noqa: E402

CHECKS = list(PESOS)
CODIGO = historico.CODIGO

ACESSIVEL = 1
RANKING = 2  # tem nota e entra no ranking geral
OFICIAL = 4  # todos os itens verificados: tem posicao no ranking e concorre a medalha
SEMANAS_POR_CIDADE = 12
HALL_MAXIMO = 30


def populacoes(raiz):
    """{ibge: habitantes} da lista de dominios (ultimo desempate do podio)."""
    caminho = Path(raiz) / "data" / "dominios.csv"
    if not caminho.exists():
        return {}
    saida = {}
    for e in ler_csv(caminho):
        try:
            saida[e.ibge] = int(e.populacao)
        except (TypeError, ValueError):
            pass
    return saida


def premios(tempo, populacao=None):
    """Podio de cada semana, medalhas de cada cidade e o hall da fama.

    Um ranking so: concorre quem teve todos os itens verificados. Chegou a ter um
    "geral" com todo mundo que tem nota, mas depois que a varredura passou a verificar
    quase tudo ele dava sempre o mesmo podio.
    """
    saida = {"semanas": [], "oficial": {}}
    for ranking in ("oficial",):
        semanas = medalhas.podios(tempo, ranking, populacao)
        por_cidade = defaultdict(list)
        for i, s in enumerate(semanas):
            for tipo in medalhas.TIPOS:
                for ibge in s[tipo]:
                    por_cidade[ibge].append([i, tipo[0]])  # o, p, b
        saida["semanas"] = [{"s": s["semana"], "d": s["data"], "parcial": s["parcial"]} for s in semanas]
        saida[ranking] = {
            "x": [s["desempate"] for s in semanas],
            "cidades": dict(por_cidade),
            "hall": medalhas.hall_da_fama(semanas)[:HALL_MAXIMO],
        }
    return saida


def compacto(obj, caminho):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))


def linha_do_tempo(dados, snapshots):
    """Junta o historico com a semana atual e avalia tudo com as regras de hoje.

    Devolve (lista de (data, avaliacao)), em ordem de data.
    """
    atual = historico.compactar(dados)
    por_data = {s["data"]: s for s in snapshots}
    por_data[atual["data"]] = atual  # a varredura atual sempre vence
    return [(data, por_data[data], historico.avaliar_snapshot(por_data[data])) for data in sorted(por_data)]


def resumir(dados, snapshots=(), populacao=None):
    """Devolve (resumo, detalhes_por_uf, evolucao_nacional)."""
    tempo = linha_do_tempo(dados, snapshots)
    _, _, agora = tempo[-1]
    antes = tempo[-2][2] if len(tempo) > 1 else {}

    linhas = []
    por_uf = defaultdict(dict)
    for r in dados["resultados"]:
        checks = r.get("checks", {})
        # "-" = item que ainda nao existia quando essa varredura rodou
        status = "".join(CODIGO.get(checks[c].get("status"), "e") if c in checks else "-" for c in CHECKS)
        nota, conceito, pos, pos_geral = agora.get(r["ibge"], [None, None, None, None])
        pos_antes = antes.get(r["ibge"], [None, None, None, None])[2]
        # positivo = subiu no ranking oficial
        variacao = pos_antes - pos if (pos is not None and pos_antes is not None) else None
        flags = (ACESSIVEL if r.get("acessivel") else 0) | (RANKING if pos_geral is not None else 0) | (OFICIAL if pos is not None else 0)
        linhas.append([
            r["ibge"], r["municipio"], r["uf"], r["dominio"],
            r.get("lat"), r.get("lon"), nota, conceito,
            flags, status, pos, variacao,
        ])
        semanas = [[data, aval[r["ibge"]][0], aval[r["ibge"]][2]] for data, _, aval in tempo if r["ibge"] in aval]
        por_uf[r["uf"] or "XX"][r["ibge"]] = {
            "d": [checks.get(c, {}).get("detalhe", "") for c in CHECKS],
            "a": r.get("avisos", []),
            "h": semanas[-SEMANAS_POR_CIDADE:],
            # pontos de excelencia (desempate do podio) que a cidade ja tem
            "x": criterios_de_excelencia(checks) if r.get("acessivel") else [],
        }

    resumo = {
        "gerado_em": dados["gerado_em"],
        "total": dados.get("total", len(linhas)),
        "amostra": dados.get("amostra"),
        "anterior": tempo[-2][0] if len(tempo) > 1 else None,
        "ranqueados": sum(1 for v in agora.values() if v[3] is not None),
        "oficiais": sum(1 for v in agora.values() if v[2] is not None),
        "checks": CHECKS,
        "campos": ["ibge", "municipio", "uf", "dominio", "lat", "lon", "nota", "conceito", "flags", "status", "pos", "var"],
        "municipios": linhas,
        "premios": premios(tempo, populacao),
    }
    evolucao = [s for s in (historico.resumo_nacional(snap, aval) for _, snap, aval in tempo) if s]
    return resumo, por_uf, evolucao


PERGUNTA = '<h1 id="manchete">O site da sua prefeitura protege você?</h1>'
TOTAL = '<strong id="n-total">milhares de</strong>'


def manchete(resumo):
    """Frase de abertura com o dado da semana. Vai direto no HTML pra nao piscar ao carregar."""
    i_dmarc = resumo["checks"].index("dmarc")
    i_flags = resumo["campos"].index("flags")
    i_status = resumo["campos"].index("status")
    ranqueados = [m for m in resumo["municipios"] if m[i_flags] & (ACESSIVEL | RANKING) == ACESSIVEL | RANKING]
    if not ranqueados:
        return None
    sem_dmarc = sum(1 for m in ranqueados if m[i_status][i_dmarc] != "p") / len(ranqueados)
    em_dez = round(sem_dmarc * 10)
    if em_dez < 3:
        return None
    return f"{em_dez} em cada 10 prefeituras deixam golpistas mandar e-mail em nome delas."


def numero_br(n):
    return f"{n:,}".replace(",", ".")


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


CORES_SELO = {"A": "#1e9e7e", "B": "#5a9e4f", "C": "#c98a12", "D": "#d0602a", "F": "#c4362a"}


def selo_svg(nota, conceito):
    """Selo no estilo dos badges do GitHub. So tem numeros e letras, nada vindo de fora."""
    esquerda = "farol-gov"
    if nota is None:
        direita, cor = "sem nota", "#7f8b96"
    else:
        direita, cor = f"{conceito} · {nota:.0f}/100", CORES_SELO.get(conceito, "#7f8b96")
    # largura aproximada pra Verdana 11px, igual os badges do shields.io
    larg_e = 10 + round(len(esquerda) * 6.6)
    larg_d = 10 + round(len(direita) * 6.8)
    total = larg_e + larg_d
    titulo = f"farol-gov: {direita}"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="20" role="img" aria-label="{titulo}">
<title>{titulo}</title>
<linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#fff" stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient>
<clipPath id="r"><rect width="{total}" height="20" rx="3" fill="#fff"/></clipPath>
<g clip-path="url(#r)"><rect width="{larg_e}" height="20" fill="#07182a"/><rect x="{larg_e}" width="{larg_d}" height="20" fill="{cor}"/><rect width="{total}" height="20" fill="url(#s)"/></g>
<g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
<text x="{larg_e / 2}" y="14" fill="#ffcf6b">{esquerda}</text>
<text x="{larg_e + larg_d / 2}" y="15" fill="#010101" fill-opacity=".3">{direita}</text>
<text x="{larg_e + larg_d / 2}" y="14">{direita}</text>
</g></svg>
"""


def gerar_selos(resumo, pasta):
    campo = {c: i for i, c in enumerate(resumo["campos"])}
    pasta.mkdir(parents=True, exist_ok=True)
    for m in resumo["municipios"]:
        ranqueado = m[campo["pos"]] is not None
        nota = m[campo["nota"]] if ranqueado else None
        (pasta / f"{m[campo['ibge']]}.svg").write_text(selo_svg(nota, m[campo["conceito"]]), encoding="utf-8")


URL = "https://guilhermeoliveirabrito.github.io/farol-gov/"


def json_ld(resumo):
    """Descricao do dataset no formato schema.org, pro Google Dataset Search achar."""
    dados = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "farol-gov: segurança dos sites e e-mails das prefeituras brasileiras",
        "description": (
            "Verificação semanal e passiva de HTTPS, TLS, HSTS, headers, DNSSEC, CAA, SPF e DMARC "
            f"nos sites de {resumo['total']} prefeituras brasileiras, com nota de 0 a 100 e histórico."
        ),
        "url": URL,
        "inLanguage": "pt-BR",
        "isAccessibleForFree": True,
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "creator": {"@type": "Person", "name": "Guilherme Oliveira de Brito Silva"},
        "spatialCoverage": {"@type": "Place", "name": "Brasil"},
        "keywords": ["segurança da informação", "prefeituras", "governo eletrônico", "DMARC", "HTTPS", "DNSSEC"],
        "distribution": [
            {"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": URL + "dados/latest.json"},
            {"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": URL + "dados/historico.json"},
        ],
    }
    if resumo.get("gerado_em"):
        dados["dateModified"] = resumo["gerado_em"]
    # "</" dentro do json fecharia a tag script antes da hora
    texto = json.dumps(dados, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'<script type="application/ld+json">{texto}</script>'


def sitemap(resumo):
    data = (resumo.get("gerado_em") or "")[:10]
    lastmod = f"<lastmod>{data}</lastmod>" if data else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{URL}</loc>{lastmod}<changefreq>weekly</changefreq></url>\n"
        "</urlset>\n"
    )


def carimbar(saida, versao_dados):
    """Cache-busting: o GitHub Pages guarda arquivos por 10 minutos, entao cada versao
    nova de app.js/estilo.css ganha um ?v=<hash> e os dados ganham a data da varredura."""
    hashes = {}
    for nome in ("app.js", "estilo.css"):
        arq = saida / nome
        if arq.exists():
            hashes[nome] = hashlib.sha256(arq.read_bytes()).hexdigest()[:10]
    for pagina in ("index.html", "404.html"):
        arq = saida / pagina
        if not arq.exists():
            continue
        html = arq.read_text(encoding="utf-8")
        for nome, h in hashes.items():
            html = html.replace(f'"{nome}"', f'"{nome}?v={h}"').replace(f'/farol-gov/{nome}"', f'/farol-gov/{nome}?v={h}"')
        if versao_dados:
            html = html.replace('href="dados/resumo.json"', f'href="dados/resumo.json?v={versao_dados}"')
            html = html.replace('<meta name="referrer"', f'<meta name="versao-dados" content="{versao_dados}">\n  <meta name="referrer"', 1)
        arq.write_text(html, encoding="utf-8")


def montar(raiz, saida):
    raiz, saida = Path(raiz), Path(saida)
    if saida.exists():
        shutil.rmtree(saida)
    shutil.copytree(raiz / "site", saida)

    resultados = raiz / "data" / "resultados" / "latest.json"
    if resultados.exists():
        dados = json.loads(resultados.read_text(encoding="utf-8"))
        snapshots = historico.carregar(raiz / "data" / "historico")
        resumo, por_uf, evolucao = resumir(dados, snapshots, populacoes(raiz))
        compacto(resumo, saida / "dados" / "resumo.json")
        compacto(evolucao, saida / "dados" / "historico.json")
        for uf, detalhes in por_uf.items():
            compacto(detalhes, saida / "dados" / "uf" / f"{uf}.json")
        compacto(dados, saida / "dados" / "latest.json")
        gerar_selos(resumo, saida / "selos")

        index = saida / "index.html"
        if index.exists():
            html = index.read_text(encoding="utf-8")
            frase = manchete(resumo)
            if frase:
                html = html.replace(PERGUNTA, f'<h1 id="manchete">{frase}</h1>')
            html = html.replace(TOTAL, f'<strong id="n-total">{numero_br(resumo["total"])}</strong>')
            html = html.replace("</head>", f"  {json_ld(resumo)}\n</head>", 1)
            index.write_text(html, encoding="utf-8")
        (saida / "sitemap.xml").write_text(sitemap(resumo), encoding="utf-8")
        print(f"{len(resumo['municipios'])} municipios no resumo, {len(evolucao)} semanas no historico")
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

    versao = None
    if resultados.exists():
        versao = hashlib.sha256(resultados.read_bytes()).hexdigest()[:10]
    carimbar(saida, versao)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raiz", default=".")
    parser.add_argument("--saida", default="_site")
    args = parser.parse_args()
    montar(args.raiz, args.saida)


if __name__ == "__main__":
    main()
