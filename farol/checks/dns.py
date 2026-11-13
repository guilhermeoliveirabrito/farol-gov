"""Checks de DNS: DNSSEC, SPF e DMARC."""
from . import ERROR, FAIL, PASS, WARN, Resultado

# resolvers publicos que validam DNSSEC
SERVIDORES_PADRAO = ("1.1.1.1", "8.8.8.8")


class ErroDNS(Exception):
    pass


class ResolverDNS:
    """Wrapper fino em cima do dnspython, pra facilitar trocar por um fake nos testes."""

    def __init__(self, servidores=SERVIDORES_PADRAO, timeout=5.0):
        import dns.flags
        import dns.resolver

        self._r = dns.resolver.Resolver(configure=False)
        self._r.nameservers = list(servidores)
        self._r.lifetime = timeout
        # DO=1 pede pro resolver validar e devolver a flag AD
        self._r.use_edns(0, dns.flags.DO, 1232)

    def _resolve(self, nome, tipo):
        import dns.exception
        import dns.resolver

        try:
            return self._r.resolve(nome, tipo, raise_on_no_answer=False)
        except dns.resolver.NXDOMAIN:
            return None
        except dns.exception.DNSException as e:
            raise ErroDNS(f"{type(e).__name__}: {e}") from e

    def txt(self, nome):
        resp = self._resolve(nome, "TXT")
        if resp is None or resp.rrset is None:
            return []
        return [b"".join(r.strings).decode("utf-8", "replace") for r in resp.rrset]

    def endereco(self, nome):
        """Retorna (existe, validado_dnssec)."""
        import dns.flags

        resp = self._resolve(nome, "A")
        if resp is None:
            return False, False
        if resp.rrset is None:
            # sem A, tenta AAAA antes de dizer que nao existe
            resp = self._resolve(nome, "AAAA")
            if resp is None or resp.rrset is None:
                return False, False
        return True, bool(resp.response.flags & dns.flags.AD)


def avaliar_spf(registros):
    spf = [r for r in registros if r.lower().startswith("v=spf1")]
    if not spf:
        return Resultado("spf", FAIL, "sem registro SPF")
    if len(spf) > 1:
        # RFC 7208 diz que mais de um registro e permerror
        return Resultado("spf", FAIL, "mais de um registro SPF (invalido)")

    termos = spf[0].lower().split()[1:]
    for termo in termos:
        if termo.lstrip("+-~?") != "all":
            continue
        qualificador = termo[0] if termo[0] in "+-~?" else "+"
        if qualificador in "-~":
            return Resultado("spf", PASS, termo)
        if qualificador == "?":
            return Resultado("spf", WARN, "?all nao bloqueia nada")
        return Resultado("spf", FAIL, "+all autoriza qualquer remetente")

    redirect = [t for t in termos if t.startswith("redirect=")]
    if redirect:
        return Resultado("spf", WARN, f"politica delegada via {redirect[0]}")
    return Resultado("spf", WARN, "registro sem mecanismo all")


def _tags_dmarc(registro):
    tags = {}
    for parte in registro.split(";"):
        if "=" in parte:
            k, v = parte.split("=", 1)
            tags[k.strip().lower()] = v.strip().lower()
    return tags


def avaliar_dmarc(registros):
    dmarc = [r for r in registros if r.replace(" ", "").lower().startswith("v=dmarc1")]
    if not dmarc:
        return Resultado("dmarc", FAIL, "sem registro DMARC")
    if len(dmarc) > 1:
        return Resultado("dmarc", FAIL, "mais de um registro DMARC (invalido)")

    politica = _tags_dmarc(dmarc[0]).get("p")
    if politica in ("reject", "quarantine"):
        return Resultado("dmarc", PASS, f"p={politica}")
    if politica == "none":
        return Resultado("dmarc", WARN, "p=none so monitora, nao bloqueia")
    return Resultado("dmarc", FAIL, "registro sem politica p= valida")


def _alvo_redirect(registros):
    for r in registros:
        if not r.lower().startswith("v=spf1"):
            continue
        termos = r.lower().split()
        if any(t.lstrip("+-~?") == "all" for t in termos):
            return None
        for t in termos:
            if t.startswith("redirect="):
                return t.split("=", 1)[1]
    return None


def checar_spf(dominio, resolver):
    try:
        registros = resolver.txt(dominio)
        # segue um nivel de redirect, que e o caso mais comum
        alvo = _alvo_redirect(registros)
        if alvo:
            final = avaliar_spf(resolver.txt(alvo))
            final.detalhe = f"via {alvo}: {final.detalhe}"
            return final
        return avaliar_spf(registros)
    except ErroDNS as e:
        return Resultado("spf", ERROR, str(e))


def checar_dmarc(dominio, resolver):
    try:
        return avaliar_dmarc(resolver.txt(f"_dmarc.{dominio}"))
    except ErroDNS as e:
        return Resultado("dmarc", ERROR, str(e))


def checar_dnssec(host, resolver):
    """Devolve (existe, Resultado). Se o host nem existe, o resto nem precisa rodar."""
    try:
        existe, validado = resolver.endereco(host)
    except ErroDNS as e:
        return True, Resultado("dnssec", ERROR, str(e))
    if not existe:
        return False, Resultado("dnssec", ERROR, "dominio nao resolve")
    if validado:
        return True, Resultado("dnssec", PASS, "resposta validada (AD)")
    return True, Resultado("dnssec", FAIL, "dominio sem DNSSEC")
