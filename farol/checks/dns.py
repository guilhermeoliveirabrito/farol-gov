"""Checks de DNS: DNSSEC, CAA, SPF e DMARC."""
import time

from . import ERROR, FAIL, PASS, WARN, Resultado

# resolvers publicos que validam DNSSEC. Com 32 threads consultando ao mesmo tempo,
# dois servidores so nao davam conta e muita consulta estourava o tempo.
SERVIDORES_PADRAO = ("1.1.1.1", "8.8.8.8", "9.9.9.9", "1.0.0.1", "8.8.4.4")


class ErroDNS(Exception):
    pass


class ResolverDNS:
    """Wrapper fino em cima do dnspython, pra facilitar trocar por um fake nos testes.

    Consulta primeiro os resolvers publicos, que validam DNSSEC (flag AD). Se eles
    nao respondem a tempo, cai pro resolver do proprio sistema (no GitHub Actions, o
    da Azure). Na varredura de 16/11 e na de 17/11 centenas de consultas estouraram o
    tempo nos resolvers publicos com o site da prefeitura funcionando normalmente, ou
    seja, o problema era do caminho ate eles, nao do DNS da cidade.
    O resolver do sistema nao valida DNSSEC, entao ele so serve pros dados (TXT, CAA,
    endereco); quando so ele responde, o DNSSEC fica como nao verificado.
    """

    def __init__(self, servidores=SERVIDORES_PADRAO, timeout=6.0, tentativas=2, reserva=True):
        import dns.flags
        import dns.resolver

        self._r = dns.resolver.Resolver(configure=False)
        self._r.nameservers = list(servidores)
        # cada servidor tem 2s pra responder; dentro do lifetime o dnspython vai trocando de servidor
        self._r.timeout = 2.0
        self._r.lifetime = timeout
        self._r.rotate = True
        # DO=1 pede pro resolver validar e devolver a flag AD
        self._r.use_edns(0, dns.flags.DO, 1232)
        self._tentativas = tentativas

        self._reserva = None
        if reserva:
            try:
                self._reserva = dns.resolver.Resolver()  # le o /etc/resolv.conf
                self._reserva.lifetime = timeout
                self._reserva.use_edns(0, 0, 1232)
            except Exception:  # sem resolv.conf (container minimo etc), segue so com os publicos
                self._reserva = None

    def _consulta(self, resolver, nome, tipo, tentativas):
        import dns.exception
        import dns.resolver

        for tentativa in range(tentativas):
            try:
                return resolver.resolve(nome, tipo, raise_on_no_answer=False)
            except dns.resolver.NXDOMAIN:
                return None
            except (dns.resolver.LifetimeTimeout, dns.resolver.NoNameservers) as e:
                if tentativa + 1 < tentativas:
                    time.sleep(1.0)
                    continue
                # a mensagem do dnspython lista cada servidor e cada tentativa; aqui basta o motivo
                raise ErroDNS(f"{type(e).__name__}: o DNS de {nome} nao respondeu a tempo") from e
            except dns.exception.DNSException as e:
                raise ErroDNS(f"{type(e).__name__}: {str(e)[:120]}") from e

    def _resolve(self, nome, tipo, validar=False):
        """Devolve (resposta, veio_do_publico).

        validar=True (so o endereco, que precisa da flag AD do DNSSEC): resolvers publicos
        primeiro e o do sistema de reserva. O resto (TXT, CAA) vai primeiro pro resolver
        do sistema, que fica do lado e nao limita a taxa; na varredura de 19/11 o dns
        pelos publicos virou o gargalo e mais de mil dominios precisaram de repescagem.
        """
        ordem = [(self._r, self._tentativas, True)]
        if self._reserva is not None:
            reserva = (self._reserva, 1, False)
            ordem = ordem + [reserva] if validar else [reserva, *ordem]
        for i, (resolver, tentativas, publico) in enumerate(ordem):
            try:
                return self._consulta(resolver, nome, tipo, tentativas), publico
            except ErroDNS:
                if i == len(ordem) - 1:
                    raise
        raise AssertionError("inalcancavel")

    def txt(self, nome):
        resp, _ = self._resolve(nome, "TXT")
        if resp is None or resp.rrset is None:
            return []
        return [b"".join(r.strings).decode("utf-8", "replace") for r in resp.rrset]

    def endereco(self, nome):
        """Retorna (existe, validado_dnssec, ips). validado_dnssec e None quando so o
        resolver do sistema respondeu (ele nao valida, entao nao da pra saber)."""
        import dns.flags

        resp, publico = self._resolve(nome, "A", validar=True)
        if resp is None:
            return False, False, []
        if resp.rrset is None:
            # sem A, tenta AAAA antes de dizer que nao existe
            resp, publico = self._resolve(nome, "AAAA", validar=True)
            if resp is None or resp.rrset is None:
                return False, False, []
        ips = sorted(r.to_text() for r in resp.rrset)
        return True, (bool(resp.response.flags & dns.flags.AD) if publico else None), ips

    def caa(self, nome):
        resp, _ = self._resolve(nome, "CAA")
        if resp is None or resp.rrset is None:
            return []
        return [r.to_text() for r in resp.rrset]


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

    tags = _tags_dmarc(dmarc[0])
    politica = tags.get("p")
    if politica in ("reject", "quarantine"):
        # rua = pra onde vao os relatorios: sem isso ninguem fica sabendo de quem tenta se passar pela prefeitura
        return Resultado("dmarc", PASS, f"p={politica}" + ("; com relatorios" if tags.get("rua") else ""))
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
    """Devolve (existe, Resultado, ips). Se o host nem existe, o resto nem precisa rodar."""
    try:
        existe, validado, ips = resolver.endereco(host)
    except ErroDNS as e:
        return True, Resultado("dnssec", ERROR, str(e)), []
    if not existe:
        return False, Resultado("dnssec", ERROR, "dominio nao resolve"), []
    if validado is None:
        # o prefixo faz a repescagem tentar de novo nos resolvers que validam
        return True, Resultado("dnssec", ERROR, "LifetimeTimeout: os resolvers que validam DNSSEC nao responderam a tempo"), ips
    if validado:
        return True, Resultado("dnssec", PASS, "resposta validada (AD)"), ips
    return True, Resultado("dnssec", FAIL, "dominio sem DNSSEC"), ips


def checar_caa(dominio, resolver, zona_responde=False):
    """CAA diz quais autoridades podem emitir certificado pro dominio.

    Pela RFC 8659 o registro vale pros subdominios, entao sobe a arvore ate achar
    (cidade.sp.gov.br -> sp.gov.br -> gov.br). Para antes do TLD.

    zona_responde: o DNS do dominio ja respondeu o endereco. Ai, se so a consulta CAA
    fica sem resposta, o problema e do servidor da prefeitura (tem servidor antigo que
    simplesmente ignora tipos de registro que nao conhece) e conta como sem CAA.
    """
    partes = dominio.rstrip(".").split(".")
    try:
        for i in range(len(partes) - 1):
            nome = ".".join(partes[i:])
            registros = [r for r in resolver.caa(nome) if " issue " in f" {r} " or " issuewild " in f" {r} "]
            if registros:
                origem = "" if i == 0 else f" (herdado de {nome})"
                return Resultado("caa", PASS, f"{len(registros)} registro(s) CAA{origem}")
    except ErroDNS as e:
        if zona_responde:
            return Resultado("caa", FAIL, f"o DNS de {nome} nao responde a consultas CAA")
        return Resultado("caa", ERROR, str(e))
    return Resultado("caa", FAIL, "qualquer autoridade pode emitir certificado para o dominio")
