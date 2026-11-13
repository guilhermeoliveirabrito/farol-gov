from .checks import PASS, WARN

# ver docs/metodologia.md antes de mexer nisso
PESOS = {
    "https": 3,
    "redirect": 2,
    "tls": 2,
    "hsts": 1,
    "headers": 1,
    "security_txt": 1,
    "dnssec": 2,
    "spf": 1,
    "dmarc": 3,
}

VALORES = {PASS: 1.0, WARN: 0.5}

FAIXAS = [(90, "A"), (75, "B"), (55, "C"), (35, "D")]


def calcular_nota(resultados):
    total = sum(PESOS.values())
    pontos = sum(PESOS.get(r.check, 0) * VALORES.get(r.status, 0.0) for r in resultados)
    return round(100 * pontos / total, 1)


def conceito(nota):
    for minimo, letra in FAIXAS:
        if nota >= minimo:
            return letra
    return "F"
