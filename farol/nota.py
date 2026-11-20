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
    # LGPD na pagina inicial (rastreador, politica de privacidade, encarregado): so detalhe
    "privacidade": 0,
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
# (chave, texto, pontos maximos). A maioria e tudo ou nada; os marcados como graduais
# (scripts_de_fora, hsts_idade) dao parte dos pontos conforme o quanto a cidade chegou perto.
DETALHES = (
    ("tls13", "TLS 1.3", 1.0),
    ("csp", "Content-Security-Policy na página", 1.0),
    ("dmarc_reject", "DMARC com p=reject: o e-mail falso é recusado, não vai para o spam", 1.0),
    ("versao_oculta", "Não mostra a versão do servidor nem do sistema do site", 1.0),
    ("mta_sts", "MTA-STS: exige criptografia no e-mail enviado para a prefeitura", 1.0),
    ("scripts_de_fora", "Poucos scripts de outros sites: cada site de fora tira 0,15", 0.75),
    ("sem_rastreadores", "Nenhum rastreador de terceiros (Google Analytics, pixel do Facebook...) na página inicial", 0.5),
    ("politica_privacidade", "Link para a política de privacidade / LGPD na página inicial", 0.5),
    ("hsts_subdominios", "HSTS cobrindo os subdomínios", 0.5),
    ("hsts_preload", "HSTS pronto para a lista de preload dos navegadores", 0.5),
    ("referrer_policy", "Referrer-Policy: não vaza o endereço da página para outros sites", 0.5),
    ("permissions_policy", "Permissions-Policy: desliga câmera, microfone e afins que o site não usa", 0.5),
    ("dmarc_relatorios", "DMARC mandando relatórios (rua=)", 0.5),
    ("spf_hardfail", "SPF terminando em -all: recusa quem não está na lista", 0.5),
    ("caa_proprio", "CAA no próprio domínio, sem depender do registro do estado", 0.5),
    ("tls_rpt", "TLS-RPT: recebe relatório quando o e-mail chega sem criptografia", 0.5),
    ("encarregado", "Encarregado de dados (LGPD) indicado na página inicial", 0.25),
    ("jquery_atual", "Sem jQuery antigo (anterior ao 3.5, com XSS conhecido)", 0.25),
    ("hsts_idade", "HSTS longo: proporcional ao max-age, cheio a partir de 2 anos", 0.25),
    ("sri", "Scripts de fora com SRI: o navegador recusa se alguém trocar o arquivo", 0.25),
    ("csp_estrita", "CSP sem unsafe-inline nem unsafe-eval", 0.25),
    ("cert_automatico", "Certificado de até 100 dias (renovação automática)", 0.25),
    ("ipv6", "Site com IPv6", 0.25),
    ("dns_dois_provedores", "Servidores DNS em pelo menos dois provedores", 0.25),
    ("coop", "Cross-Origin-Opener-Policy: isola a página de janelas abertas por outros sites", 0.25),
    ("cookies_samesite", "Cookies com SameSite (ou nenhum cookie na página inicial)", 0.25),
    ("security_txt_expires", "security.txt com validade (Expires)", 0.25),
    ("nome_oculto", "Não mostra nem o nome do software do servidor", 0.25),
    ("redirect_permanente", "Redirecionamento para HTTPS permanente (301/308): o navegador nem tenta mais o HTTP", 0.1),
    ("cert_com_e_sem_www", "Certificado vale com e sem www", 0.1),
    ("corp", "Cross-Origin-Resource-Policy: outro site não embute os arquivos da prefeitura", 0.1),
    ("coep", "Cross-Origin-Embedder-Policy", 0.1),
    ("caa_sem_curinga", "CAA proíbe certificado curinga (*.dominio)", 0.1),
    ("dmarc_estrito", "DMARC com alinhamento estrito (adkim=s ou aspf=s)", 0.1),
    ("caa_iodef", "CAA com iodef: avisa a prefeitura se alguém pedir certificado indevido", 0.1),
)
PONTOS_DETALHE = {chave: pontos for chave, _, pontos in DETALHES}
DOIS_ANOS = 2 * 365 * 86400


def detalhes_obtidos(checks):
    """checks: {nome: {"status", "detalhe"}} como no json da varredura.

    Devolve {chave: pontos} so dos detalhes que deram algum ponto, na ordem de DETALHES."""

    def cumpre(nome, *status):
        c = checks.get(nome) or {}
        return str(c.get("detalhe", "")) if c.get("status") in (status or ("pass",)) else None

    obtido = {}

    def ganha(chave, fracao=1.0):
        if fracao > 0:
            obtido[chave] = round(PONTOS_DETALHE[chave] * min(fracao, 1.0), 2)

    tls, hsts, headers = cumpre("tls"), cumpre("hsts"), cumpre("headers")
    dmarc, spf, caa = cumpre("dmarc"), cumpre("spf"), cumpre("caa")
    cookies, sec, versao, email = cumpre("cookies"), cumpre("security_txt"), cumpre("versao_exposta"), cumpre("email_tls")
    if tls == "TLSv1.3":
        ganha("tls13")
    if hsts is not None:
        h = hsts.lower()
        if "includesubdomains" in h:
            ganha("hsts_subdominios")
        if "preload" in h:
            ganha("hsts_preload")
        idade = re.match(r"max-age=(\d+)", h)
        if idade:
            ganha("hsts_idade", int(idade.group(1)) / DOIS_ANOS)
    if headers is not None:
        for chave, texto in (
            ("csp", "CSP"), ("csp_estrita", "CSP estrita"), ("referrer_policy", "Referrer-Policy"),
            ("permissions_policy", "Permissions-Policy"), ("coop", "COOP"), ("corp", "CORP"), ("coep", "COEP"),
        ):
            if re.search(rf"(?:com |, ){re.escape(texto)}(?:,|$)", headers):
                ganha(chave)
    misto = cumpre("conteudo_misto", "pass", "warn")
    if misto is not None:
        if "nenhum script de fora" in misto:
            ganha("scripts_de_fora")
        m = re.search(r"scripts de (\d+) site", misto)
        if m:
            # cada site de fora tira 0,15 dos 0,75
            ganha("scripts_de_fora", 1 - int(m.group(1)) / 5)
        if "todos com SRI" in misto:
            ganha("sri")
        jq = re.search(r"jQuery ([\d.]+|sem versao)", misto)
        if jq is None:
            ganha("jquery_atual")  # nem carrega jquery
        elif jq.group(1) != "sem versao":
            versao_jq = tuple(int(x) for x in jq.group(1).split(".") if x)
            if versao_jq >= (3, 5):
                ganha("jquery_atual")
    https = cumpre("https", "pass", "warn")
    if https is not None:
        m = re.search(r"certificado de (\d+) dias", https)
        if m and int(m.group(1)) <= 100:
            ganha("cert_automatico")
        if "vale com e sem www" in https:
            ganha("cert_com_e_sem_www")
    redirect = cumpre("redirect")
    if redirect is not None and "(permanente" in redirect:
        ganha("redirect_permanente")
    dns = str((checks.get("dnssec") or {}).get("detalhe", ""))
    if "IPv6" in dns:
        ganha("ipv6")
    m = re.search(r"em (\d+) provedor", dns)
    if m and int(m.group(1)) >= 2:
        ganha("dns_dois_provedores")
    if dmarc is not None:
        if dmarc.startswith("p=reject") and "pct=" not in dmarc:
            ganha("dmarc_reject")
        if "com relatorios" in dmarc:
            ganha("dmarc_relatorios")
        if "alinhamento estrito" in dmarc:
            ganha("dmarc_estrito")
    if spf is not None and spf.endswith("-all"):
        ganha("spf_hardfail")
    if caa is not None:
        if "herdado" not in caa:
            ganha("caa_proprio")
        if "iodef" in caa:
            ganha("caa_iodef")
        if "sem curinga" in caa:
            ganha("caa_sem_curinga")
    if cookies is not None and "sem SameSite" not in cookies:
        ganha("cookies_samesite")
    if sec is not None and "e Expires" in sec:
        ganha("security_txt_expires")
    if versao is not None:
        ganha("versao_oculta")
        if versao == "nao mostra o software":
            ganha("nome_oculto")
    if email is not None:
        ganha("mta_sts")
        if "e TLS-RPT" in email:
            ganha("tls_rpt")
    elif (checks.get("email_tls") or {}).get("status") == "warn":
        ganha("tls_rpt")
    priv = (checks.get("privacidade") or {})
    if priv.get("status") in ("pass", "warn", "fail"):
        d = str(priv.get("detalhe", ""))
        if "sem rastreadores" in d:
            ganha("sem_rastreadores")
        if "com link de privacidade" in d:
            ganha("politica_privacidade")
        if "encarregado indicado" in d:
            ganha("encarregado")
    return {chave: obtido[chave] for chave, _, _ in DETALHES if chave in obtido}


def detalhes_feitos(checks):
    """So as chaves dos detalhes que deram algum ponto."""
    return list(detalhes_obtidos(checks))


def pontos_de_detalhe(checks):
    return round(sum(detalhes_obtidos(checks).values()), 2)
