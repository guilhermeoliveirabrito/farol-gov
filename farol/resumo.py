"""Gera um resumo em markdown a partir do json da varredura."""
from collections import Counter, defaultdict

from .checks import PASS, WARN
from .nota import PESOS

NOMES = {
    "https": "HTTPS com certificado válido",
    "redirect": "HTTP redireciona para HTTPS",
    "tls": "TLS 1.2 ou superior",
    "hsts": "HSTS (1 ano ou mais)",
    "headers": "Headers de segurança",
    "security_txt": "security.txt",
    "dnssec": "DNSSEC",
    "spf": "SPF",
    "dmarc": "DMARC bloqueando e-mail falso",
}


def _pct(parte, total):
    return f"{100 * parte / total:.1f}%" if total else "-"


def gerar_markdown(dados, top=20):
    todos = dados["resultados"]
    ok = [r for r in todos if r["acessivel"]]
    linhas = [
        "# Resultados",
        "",
        f"Varredura de {dados['gerado_em'][:10]}. "
        f"{len(todos)} domínios verificados, {len(ok)} acessíveis "
        f"({len(todos) - len(ok)} não responderam e ficaram fora da nota).",
        "",
        "Metodologia: [docs/metodologia.md](docs/metodologia.md). "
        "Dados completos: [data/resultados/latest.json](data/resultados/latest.json).",
        "",
        "## Conceitos",
        "",
        "| Conceito | Municípios | % |",
        "|---|---|---|",
    ]
    contagem = Counter(r["conceito"] for r in ok)
    for letra in "ABCDF":
        linhas.append(f"| {letra} | {contagem[letra]} | {_pct(contagem[letra], len(ok))} |")

    linhas += ["", "## Adoção de cada item", "", "| Item | Atende | Parcial |", "|---|---|---|"]
    for check in PESOS:
        st = [r["checks"].get(check, {}).get("status") for r in ok]
        linhas.append(
            f"| {NOMES[check]} | {_pct(st.count(PASS), len(ok))} | {_pct(st.count(WARN), len(ok))} |"
        )

    por_uf = defaultdict(list)
    for r in ok:
        por_uf[r["uf"]].append(r["nota"])
    ranking = sorted(por_uf.items(), key=lambda kv: sum(kv[1]) / len(kv[1]), reverse=True)

    linhas += ["", "## Ranking por estado", "", "| # | UF | Nota média | Municípios avaliados |", "|---|---|---|---|"]
    for i, (uf, notas) in enumerate(ranking, 1):
        linhas.append(f"| {i} | {uf} | {sum(notas) / len(notas):.1f} | {len(notas)} |")

    melhores = sorted(ok, key=lambda r: (-r["nota"], r["municipio"]))[:top]
    linhas += ["", f"## Top {top} municípios", "", "| Município | UF | Domínio | Nota |", "|---|---|---|---|"]
    for r in melhores:
        linhas.append(f"| {r['municipio']} | {r['uf']} | `{r['dominio']}` | {r['nota']} ({r['conceito']}) |")

    return "\n".join(linhas) + "\n"
