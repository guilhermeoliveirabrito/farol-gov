from .checks import ERROR, PASS, WARN

# versao da metodologia; muda quando entra/sai item ou peso, pra nao comparar nota de regras diferentes
METODOLOGIA = 2

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
    "dnssec": 2,
    "caa": 1,
    "spf": 1,
    "dmarc": 3,
}

VALORES = {PASS: 1.0, WARN: 0.5}

FAIXAS = [(90, "A"), (75, "B"), (55, "C"), (35, "D")]

# se menos que isso do peso total foi verificado, nao da pra dar nota com seguranca
COBERTURA_MINIMA = 0.7


def calcular_nota(resultados):
    """Nota de 0 a 100 considerando so os itens que deu pra verificar.

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
    pontos = sum(PESOS[r.check] * VALORES.get(r.status, 0.0) for r in verificados)
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
    "caa_proprio": "CAA no proprio dominio, sem depender do registro do estado",
}


def criterios_de_excelencia(checks):
    """checks: {nome: {"status", "detalhe"}} como no json da varredura. Devolve as chaves atingidas."""

    def detalhe(nome):
        c = checks.get(nome) or {}
        return str(c.get("detalhe", "")) if c.get("status") == "pass" else ""

    feitos = []
    if detalhe("dmarc") == "p=reject":
        feitos.append("dmarc_reject")
    if "-all" in detalhe("spf"):
        feitos.append("spf_hardfail")
    if detalhe("tls") == "TLSv1.3":
        feitos.append("tls13")
    hsts = detalhe("hsts").lower()
    if "includesubdomains" in hsts:
        feitos.append("hsts_subdominios")
    if "preload" in hsts:
        feitos.append("hsts_preload")
    if "com CSP" in detalhe("headers"):
        feitos.append("csp")
    caa = detalhe("caa")
    if caa and "herdado" not in caa:
        feitos.append("caa_proprio")
    return feitos


def excelencia(checks):
    return len(criterios_de_excelencia(checks))
