import re

from .checks import ERROR, PASS, WARN

# versao da metodologia; muda quando entra/sai item ou peso, pra nao comparar nota de regras diferentes
# 5: a nota base volta a ser a da metodologia 2 (cumpre = 100% do item, parcial = 50%)
#    e os detalhes viram pontos pequenos somados por cima, que desempatam (DETALHES)
METODOLOGIA = 5

# ver docs/metodologia.md antes de mexer nisso. A ordem aqui e a ordem que aparece na pagina.
PESOS = {
    "https": 3,
    "redirect": 2,
    "tls": 2,
    "tls_antigo": 1,
    "hsts": 1,
    "headers": 1,
    "conteudo_misto": 1,
    "cookies": 1,
    "security_txt": 1,
    # os dois abaixo sao verificados e aparecem na pagina, mas nao entram na nota base:
    # valem como detalhe (ver DETALHES)
    "versao_exposta": 0,
    "dnssec": 2,
    "caa": 1,
    "spf": 1,
    "dmarc": 3,
    "email_tls": 0,
}

VALORES = {PASS: 1.0, WARN: 0.5}

FAIXAS = [(90, "A"), (75, "B"), (55, "C"), (35, "D")]

# precisa ter verificado pelo menos 70% do peso pra ganhar nota
COBERTURA_MINIMA = 0.7


def grau(check, status, detalhe=""):
    """Quanto do item conta na nota base: cumpre 1, parcial 0,5, o resto 0.

    Na metodologia 3 e 4 o item cumprido perdia um pouco quando parava no minimo (TLS 1.2,
    DMARC quarantine...). Isso derrubou a nota de todo mundo. Esses detalhes agora somam
    pontos por cima da nota base (DETALHES), em vez de descontar dela.
    """
    return VALORES.get(status, 0.0)


def calcular_nota(resultados, graus=None):
    """Nota de 0 a 100 considerando so os itens que deu pra verificar.

    graus: {check: 0..1} ja calculado (vem do historico); sem ele, sai de grau().

    Item com `error` (timeout nosso, DNS que nao respondeu) sai da conta em vez de
    valer zero: a prefeitura nao deve perder ponto por uma falha da varredura.
    Se faltar verificacao demais, devolve None.
    """
    avaliados = [r for r in resultados if r.check in PESOS]
    verificados = [r for r in avaliados if r.status != ERROR]
    # a cobertura e medida sobre os itens que existiam na varredura (semanas antigas tinham menos)
    peso_total = sum(PESOS[r.check] for r in avaliados)
    peso_verificado = sum(PESOS[r.check] for r in verificados)
    if not peso_verificado or peso_verificado < COBERTURA_MINIMA * peso_total:
        return None
    def valor(r):
        if graus is not None and r.check in graus:
            return graus[r.check]
        return grau(r.check, r.status, r.detalhe)

    pontos = sum(PESOS[r.check] * valor(r) for r in verificados)
    return round(100 * pontos / peso_verificado, 1)


def conceito(nota):
    for minimo, letra in FAIXAS:
        if nota >= minimo:
            return letra
    return "F"


# detalhes: cada um soma poucos pontos (1, 0,5, 0,25 ou 0,1) por cima da nota base.
# A nota base mede o essencial e vale muito mais (cada item essencial vale 5 pontos ou
# mais); os detalhes sao o passo alem do minimo e servem pra separar quem fez o
# essencial igual. (chave, texto, pontos)
DETALHES = (
    ("tls13", "TLS 1.3", 1.0),
    ("csp", "Content-Security-Policy na página", 1.0),
    ("dmarc_reject", "DMARC com p=reject: o e-mail falso é recusado, não vai para o spam", 1.0),
    ("versao_oculta", "Não mostra a versão do servidor nem do sistema do site", 1.0),
    ("mta_sts", "MTA-STS: exige criptografia no e-mail enviado para a prefeitura", 1.0),
    ("hsts_subdominios", "HSTS cobrindo os subdomínios", 0.5),
    ("hsts_preload", "HSTS pronto para a lista de preload dos navegadores", 0.5),
    ("referrer_policy", "Referrer-Policy: não vaza o endereço da página para outros sites", 0.5),
    ("permissions_policy", "Permissions-Policy: desliga câmera, microfone e afins que o site não usa", 0.5),
    ("dmarc_relatorios", "DMARC mandando relatórios (rua=)", 0.5),
    ("spf_hardfail", "SPF terminando em -all: recusa quem não está na lista", 0.5),
    ("caa_proprio", "CAA no próprio domínio, sem depender do registro do estado", 0.5),
    ("tls_rpt", "TLS-RPT: recebe relatório quando o e-mail chega sem criptografia", 0.5),
    ("sem_scripts_de_fora", "Nenhum script carregado de outro site na página inicial", 0.5),
    ("poucos_scripts_de_fora", "Scripts de no máximo 3 sites de fora", 0.25),
    ("sri", "Scripts de fora com SRI: o navegador recusa se alguém trocar o arquivo", 0.25),
    ("csp_estrita", "CSP sem unsafe-inline nem unsafe-eval", 0.25),
    ("cert_automatico", "Certificado de até 100 dias (renovação automática)", 0.25),
    ("ipv6", "Site com IPv6", 0.25),
    ("dns_dois_provedores", "Servidores DNS em pelo menos dois provedores", 0.25),
    ("hsts_2_anos", "HSTS valendo por 2 anos ou mais", 0.25),
    ("coop", "Cross-Origin-Opener-Policy: isola a página de janelas abertas por outros sites", 0.25),
    ("cookies_samesite", "Cookies com SameSite (ou nenhum cookie na página inicial)", 0.25),
    ("security_txt_expires", "security.txt com validade (Expires)", 0.25),
    ("nome_oculto", "Não mostra nem o nome do software do servidor", 0.25),
    ("dmarc_estrito", "DMARC com alinhamento estrito (adkim=s ou aspf=s)", 0.1),
    ("caa_iodef", "CAA com iodef: avisa a prefeitura se alguém pedir certificado indevido", 0.1),
)
PONTOS_DETALHE = {chave: pontos for chave, _, pontos in DETALHES}


def detalhes_feitos(checks):
    """checks: {nome: {"status", "detalhe"}} como no json da varredura. Devolve as chaves cumpridas."""

    def cumpre(nome, *status):
        c = checks.get(nome) or {}
        return str(c.get("detalhe", "")) if c.get("status") in (status or ("pass",)) else None

    feitos = set()
    tls, hsts, headers = cumpre("tls"), cumpre("hsts"), cumpre("headers")
    dmarc, spf, caa = cumpre("dmarc"), cumpre("spf"), cumpre("caa")
    cookies, sec, versao, email = cumpre("cookies"), cumpre("security_txt"), cumpre("versao_exposta"), cumpre("email_tls")
    if tls == "TLSv1.3":
        feitos.add("tls13")
    if hsts is not None:
        h = hsts.lower()
        if "includesubdomains" in h:
            feitos.add("hsts_subdominios")
        if "preload" in h:
            feitos.add("hsts_preload")
        idade = re.match(r"max-age=(\d+)", h)
        if idade and int(idade.group(1)) >= 2 * 365 * 86400:
            feitos.add("hsts_2_anos")
    if headers is not None:
        for chave, texto in (
            ("csp", "CSP"), ("csp_estrita", "CSP estrita"), ("referrer_policy", "Referrer-Policy"),
            ("permissions_policy", "Permissions-Policy"), ("coop", "COOP"),
        ):
            if texto in headers:
                feitos.add(chave)
    misto = cumpre("conteudo_misto", "pass", "warn")
    if misto is not None:
        if "nenhum script de fora" in misto:
            feitos.add("sem_scripts_de_fora")
        m = re.search(r"scripts de (\d+) site", misto)
        if m and int(m.group(1)) <= 3:
            feitos.add("poucos_scripts_de_fora")
        if "todos com SRI" in misto:
            feitos.add("sri")
    https = cumpre("https", "pass", "warn")
    if https is not None:
        m = re.search(r"certificado de (\d+) dias", https)
        if m and int(m.group(1)) <= 100:
            feitos.add("cert_automatico")
    dns = str((checks.get("dnssec") or {}).get("detalhe", ""))
    if "IPv6" in dns:
        feitos.add("ipv6")
    m = re.search(r"em (\d+) provedor", dns)
    if m and int(m.group(1)) >= 2:
        feitos.add("dns_dois_provedores")
    if dmarc is not None:
        if dmarc.startswith("p=reject") and "pct=" not in dmarc:
            feitos.add("dmarc_reject")
        if "com relatorios" in dmarc:
            feitos.add("dmarc_relatorios")
        if "alinhamento estrito" in dmarc:
            feitos.add("dmarc_estrito")
    if spf is not None and spf.endswith("-all"):
        feitos.add("spf_hardfail")
    if caa is not None:
        if "herdado" not in caa:
            feitos.add("caa_proprio")
        if "iodef" in caa:
            feitos.add("caa_iodef")
    if cookies is not None and "sem SameSite" not in cookies:
        feitos.add("cookies_samesite")
    if sec is not None and "e Expires" in sec:
        feitos.add("security_txt_expires")
    if versao is not None:
        feitos.add("versao_oculta")
        if versao == "nao mostra o software":
            feitos.add("nome_oculto")
    if email is not None:
        feitos.add("mta_sts")
        if "e TLS-RPT" in email:
            feitos.add("tls_rpt")
    elif (checks.get("email_tls") or {}).get("status") == "warn":
        feitos.add("tls_rpt")
    return [chave for chave, _, _ in DETALHES if chave in feitos]


def pontos_de_detalhe(checks):
    return round(sum(PONTOS_DETALHE[c] for c in detalhes_feitos(checks)), 2)
