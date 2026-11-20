import re

from .checks import ERROR, PASS, WARN

# versao da metodologia; muda quando entra/sai item ou peso, pra nao comparar nota de regras diferentes
# 3: item cumprido deixou de valer sempre 100% (ver grau)
# 4: versao_exposta e email_tls, e graus em cookies, conteudo misto, security.txt e dmarc
METODOLOGIA = 4

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
    "versao_exposta": 1,
    "dnssec": 2,
    "caa": 1,
    "spf": 1,
    "dmarc": 3,
    "email_tls": 1,
}

VALORES = {PASS: 1.0, WARN: 0.5}
# o que vale um item parcial quando o parcial e bem fraco (p=none no DMARC so monitora,
# ?all no SPF nao bloqueia nada, so um dos dois headers basicos)
PARCIAL_FRACO = {"dmarc": 0.3, "spf": 0.3, "headers": 0.3}


def grau(check, status, detalhe=""):
    """Quanto do item a cidade cumpre, de 0 a 1, em passos de 0,05.

    Ate a metodologia 2 todo item cumprido valia 100%, e com 13 itens a nota so tinha
    umas 30 combinacoes: 565 cidades empatadas na mesma nota, 29 no topo. Agora o
    item cumprido perde um pouco quando para no minimo (TLS 1.2 em vez de 1.3, DMARC
    quarantine em vez de reject, SPF ~all em vez de -all, CAA herdado do estado...).
    Sem detalhe (testes, historico antigo) vale o cheio.
    """
    d = detalhe or ""
    if status == WARN:
        if check == "cookies":
            # "1 de 4 cookie(s) sem HttpOnly": quanto mais cookie exposto, menos vale
            m = re.match(r"(\d+) de (\d+)", d)
            if m and int(m.group(2)):
                return round(round((0.7 - 0.4 * int(m.group(1)) / int(m.group(2))) * 20) / 20, 2)
        if check == "conteudo_misto":
            m = re.match(r"(\d+) ", d)
            if m:
                n = int(m.group(1))
                return 0.7 if n == 1 else 0.5 if n <= 3 else 0.3
        return PARCIAL_FRACO.get(check, VALORES[WARN])
    if status != PASS:
        return 0.0
    g = 1.0
    if check == "tls" and d.startswith("TLSv1.2"):
        g -= 0.2
    elif check == "hsts" and d.startswith("max-age="):
        dl = d.lower()
        m = re.match(r"max-age=(\d+)", dl)
        g -= 0.0 if "includesubdomains" in dl else 0.2
        g -= 0.0 if "preload" in dl else 0.1
        g -= 0.0 if (m and int(m.group(1)) >= 2 * 365 * 86400) else 0.1
    elif check == "headers" and d.startswith("nosniff e anti-clickjacking"):
        g -= 0.0 if "CSP" in d else 0.2
        g -= 0.0 if "Referrer-Policy" in d else 0.1
        g -= 0.0 if "Permissions-Policy" in d else 0.1
    elif check == "dmarc" and d.startswith("p="):
        g -= 0.15 if d.startswith("p=quarantine") else 0.0
        g -= 0.0 if "com relatorios" in d else 0.1
        g -= 0.1 if "pct=" in d else 0.0
    elif (
        (check == "spf" and d.endswith("~all"))
        or (check == "caa" and "herdado" in d)
        or (check == "security_txt" and "sem Expires" in d)
        or (check == "email_tls" and "sem TLS-RPT" in d)
    ):
        g -= 0.2
    elif (check == "cookies" and "sem SameSite" in d) or (check == "versao_exposta" and d.startswith("mostra so o nome")):
        g -= 0.1
    return round(round(g * 20) / 20, 2)

FAIXAS = [(90, "A"), (75, "B"), (55, "C"), (35, "D")]

# se menos que isso do peso total foi verificado, nao da pra dar nota com seguranca
COBERTURA_MINIMA = 0.7


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


# pontos de excelencia: nao mudam a nota, servem pra desempatar o podio da semana.
# cada um e um passo alem do minimo que o item ja cobra
EXCELENCIA = {
    "dmarc_reject": "DMARC com p=reject (recusa o e-mail falso em vez de mandar pro spam)",
    "spf_hardfail": "SPF terminando em -all (recusa quem nao esta na lista)",
    "tls13": "TLS 1.3",
    "hsts_subdominios": "HSTS cobrindo os subdominios (includeSubDomains)",
    "hsts_preload": "HSTS pronto pra lista de preload dos navegadores",
    "csp": "Content-Security-Policy na pagina",
    "referrer_policy": "Referrer-Policy (nao vaza o endereco da pagina pra outros sites)",
    "permissions_policy": "Permissions-Policy (desliga camera, microfone etc. que o site nao usa)",
    "hsts_2_anos": "HSTS valendo por 2 anos ou mais",
    "dmarc_relatorios": "DMARC mandando relatorios (rua=)",
    "caa_proprio": "CAA no proprio dominio, sem depender do registro do estado",
}


def criterios_de_excelencia(checks):
    """checks: {nome: {"status", "detalhe"}} como no json da varredura. Devolve as chaves atingidas."""

    def detalhe(nome):
        c = checks.get(nome) or {}
        return str(c.get("detalhe", "")) if c.get("status") == "pass" else ""

    feitos = []
    dmarc = detalhe("dmarc")
    if dmarc.startswith("p=reject"):
        feitos.append("dmarc_reject")
    if "com relatorios" in dmarc:
        feitos.append("dmarc_relatorios")
    if "-all" in detalhe("spf"):
        feitos.append("spf_hardfail")
    if detalhe("tls") == "TLSv1.3":
        feitos.append("tls13")
    hsts = detalhe("hsts").lower()
    if "includesubdomains" in hsts:
        feitos.append("hsts_subdominios")
    if "preload" in hsts:
        feitos.append("hsts_preload")
    idade = re.match(r"max-age=(\d+)", hsts)
    if idade and int(idade.group(1)) >= 2 * 365 * 86400:
        feitos.append("hsts_2_anos")
    headers = detalhe("headers")
    for chave, texto in (("csp", "CSP"), ("referrer_policy", "Referrer-Policy"), ("permissions_policy", "Permissions-Policy")):
        if texto in headers:
            feitos.append(chave)
    caa = detalhe("caa")
    if caa and "herdado" not in caa:
        feitos.append("caa_proprio")
    return feitos


def excelencia(checks):
    return len(criterios_de_excelencia(checks))
