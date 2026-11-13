import argparse
import json
import logging
import sys
from pathlib import Path

from . import __version__
from .checks.dns import ResolverDNS
from .checks.web import ClienteHTTP
from .dominios import Entidade, ler_csv, normalizar_host
from .resumo import gerar_markdown
from .scanner import avaliar, varrer

CORES = {"pass": "\033[32m", "warn": "\033[33m", "fail": "\033[31m", "error": "\033[90m"}
RESET = "\033[0m"


def cmd_check(args):
    host = normalizar_host(args.dominio)
    ent = Entidade(ibge="", municipio="", uf="", dominio=host)
    r = avaliar(ent, ResolverDNS(), ClienteHTTP(timeout=args.timeout))

    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0

    cor = sys.stdout.isatty()
    print(f"\n{host}\n")
    for nome, c in r["checks"].items():
        status = c["status"].upper().ljust(5)
        if cor:
            status = CORES[c["status"]] + status + RESET
        print(f"  {status}  {nome.ljust(13)} {c['detalhe']}")
    if r["acessivel"]:
        print(f"\n  nota: {r['nota']} ({r['conceito']})\n")
    else:
        print("\n  dominio inacessivel, sem nota\n")
    return 0


def cmd_scan(args):
    entidades = ler_csv(args.csv)
    if args.limite:
        entidades = entidades[: args.limite]
    print(f"varrendo {len(entidades)} dominios com {args.workers} workers...", file=sys.stderr)

    def progresso(i, total):
        if i % 100 == 0 or i == total:
            print(f"  {i}/{total}", file=sys.stderr)

    cliente = ClienteHTTP(timeout=args.timeout)
    dados = varrer(entidades, ResolverDNS, cliente, workers=args.workers, progresso=progresso)

    saida = Path(args.saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"salvo em {saida}", file=sys.stderr)
    return 0


def cmd_resumo(args):
    dados = json.loads(Path(args.json).read_text(encoding="utf-8"))
    md = gerar_markdown(dados, top=args.top)
    if args.saida:
        Path(args.saida).write_text(md, encoding="utf-8")
    else:
        print(md)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="farol", description="Higiene de seguranca de dominios do governo")
    parser.add_argument("--version", action="version", version=f"farol {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("check", help="verifica um unico dominio")
    p.add_argument("dominio")
    p.add_argument("--json", action="store_true", help="saida em json")
    p.add_argument("--timeout", type=float, default=10.0)
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("scan", help="verifica todos os dominios de um csv")
    p.add_argument("csv")
    p.add_argument("-o", "--saida", default="data/resultados/latest.json")
    p.add_argument("-w", "--workers", type=int, default=32)
    p.add_argument("--timeout", type=float, default=10.0)
    p.add_argument("--limite", type=int, help="so os N primeiros (pra testar)")
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("resumo", help="gera o markdown com ranking a partir do json")
    p.add_argument("json")
    p.add_argument("-o", "--saida")
    p.add_argument("--top", type=int, default=20)
    p.set_defaults(func=cmd_resumo)

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
