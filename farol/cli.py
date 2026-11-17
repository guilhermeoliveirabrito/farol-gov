import argparse
import csv
import json
import logging
import os
import random
import sys
from pathlib import Path

from . import __version__, historico
from .checks.dns import ResolverDNS
from .checks.web import ClienteHTTP
from .dominios import Entidade, ler_csv, normalizar_host
from .resumo import gerar_markdown, linhas_movimento, linhas_revisao
from .scanner import avaliar, varrer
from .validacao import validar

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
        print(f"  {status}  {nome.ljust(15)} {c['detalhe']}")
    if r["acessivel"]:
        print(f"\n  nota: {r['nota']} ({r['conceito']})\n")
    else:
        print("\n  dominio inacessivel, sem nota\n")
    return 0


def cmd_scan(args):
    entidades = ler_csv(args.csv)
    if args.amostra:
        # amostra aleatoria pra teste: o --limite pega so o comeco da lista (que e tudo do Norte)
        entidades = random.Random(args.semente).sample(entidades, min(args.amostra, len(entidades)))
    elif args.limite:
        entidades = entidades[: args.limite]
    print(f"varrendo {len(entidades)} dominios com {args.workers} workers...", file=sys.stderr)

    def progresso(i, total):
        if i % 100 == 0 or i == total:
            print(f"  {i}/{total}", file=sys.stderr)

    cliente = ClienteHTTP(timeout=args.timeout)
    # repescagem com o dobro de paciencia
    lento = ClienteHTTP(timeout=args.timeout * 2.5, tentativas=2)
    dados = varrer(entidades, ResolverDNS, cliente, workers=args.workers, progresso=progresso, cliente_lento=lento, por_ip=args.por_ip, prazo=args.prazo * 60)
    rep = dados["repescagem"]
    print(f"repescagem: {rep['recuperados']} de {rep['tentados']} recuperados, {rep['fora_do_prazo']} fora do prazo", file=sys.stderr)
    if dados["sem_visita_por_prazo"]:
        print(f"atencao: {dados['sem_visita_por_prazo']} sites ficaram sem visita porque o prazo acabou", file=sys.stderr)
    # a pagina mostra um aviso quando o resultado e so uma amostra
    dados["amostra"] = args.amostra or args.limite or None

    saida = Path(args.saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"salvo em {saida}", file=sys.stderr)
    if dados["repescagem"].get("fora_do_prazo") or dados.get("sem_visita_por_prazo"):
        # sobrou thread da repescagem presa em servidor lento; o resultado ja esta salvo,
        # entao nao vale esperar o python juntar essas threads na saida
        sys.stderr.flush()
        os._exit(0)
    return 0


def cmd_resumo(args):
    dados = json.loads(Path(args.json).read_text(encoding="utf-8"))
    md = gerar_markdown(dados, top=args.top)
    if args.historico:
        md += "\n".join(linhas_movimento(dados, historico.carregar(args.historico))) + "\n"
    if args.revisao:
        revisao = linhas_revisao(dados)
        with open(args.revisao, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["ibge", "municipio", "uf", "dominio_wikidata", "motivo"])
            w.writeheader()
            w.writerows(revisao)
        print(f"{len(revisao)} entradas pra revisar em {args.revisao}", file=sys.stderr)
    if args.saida:
        Path(args.saida).write_text(md, encoding="utf-8")
    else:
        print(md)
    return 0


def cmd_arquivar(args):
    dados = json.loads(Path(args.json).read_text(encoding="utf-8"))
    destino = historico.salvar(dados, args.pasta)
    print(f"historico salvo em {destino}", file=sys.stderr)
    return 0


def cmd_validar(args):
    dados = json.loads(Path(args.json).read_text(encoding="utf-8"))
    problemas, linhas = validar(dados, historico.carregar(args.historico) if args.historico else [])
    relatorio = ["## Validacao da varredura", "", *linhas, ""]
    if problemas:
        relatorio += ["**Nao publicada.** O site e o historico continuam com a varredura anterior:", ""]
        relatorio += [f"- {p}" for p in problemas]
    else:
        relatorio.append("Tudo dentro do esperado, pode publicar.")
    print("\n".join(relatorio))
    return 1 if problemas else 0


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
    p.add_argument("--por-ip", type=int, default=3, help="verificacoes simultaneas no mesmo servidor")
    p.add_argument("--prazo", type=float, default=75, help="minutos; quem nao for visitado ate la fica sem nota nesta rodada")
    p.add_argument("--limite", type=int, help="so os N primeiros (pra testar)")
    p.add_argument("--amostra", type=int, help="N dominios aleatorios (pra testar)")
    p.add_argument("--semente", type=int, default=42, help="semente da amostra")
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("resumo", help="gera o markdown com ranking a partir do json")
    p.add_argument("json")
    p.add_argument("-o", "--saida")
    p.add_argument("--top", type=int, default=20)
    p.add_argument("--revisao", help="salva um csv com os dominios que precisam de revisao no wikidata")
    p.add_argument("--historico", help="pasta do historico, pra incluir quem subiu e quem caiu")
    p.set_defaults(func=cmd_resumo)

    p = sub.add_parser("validar", help="confere se a varredura esta boa pra publicar (sai com erro se nao)")
    p.add_argument("json")
    p.add_argument("--historico", default="data/historico", help="pasta do historico, pra comparar com a anterior")
    p.set_defaults(func=cmd_validar)

    p = sub.add_parser("arquivar", help="guarda a varredura no historico semanal (formato compacto)")
    p.add_argument("json")
    p.add_argument("--pasta", default="data/historico")
    p.set_defaults(func=cmd_arquivar)

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
