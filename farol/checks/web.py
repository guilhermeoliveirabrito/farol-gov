"""Checks web: HTTPS, redirecionamento, TLS, HSTS, headers e security.txt.

Usa só a biblioteca padrão. Tudo aqui é GET simples, igual um navegador faria.
"""
import http.client
import re
import socket
import ssl
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit

from farol import USER_AGENT

from . import ERROR, FAIL, PASS, WARN, Resultado

REDIRECTS = (301, 302, 303, 307, 308)
TLS_OK = ("TLSv1.2", "TLSv1.3")
HSTS_MINIMO = 31536000  # 1 ano


@dataclass
class Resposta:
    url: str
    status: int
    headers: dict = field(default_factory=dict)
    corpo: bytes = b""
    tls: str | None = None


class ErroConexao(Exception):
    # tipo: certificado, tls, recusada, dns, timeout, outro
    def __init__(self, tipo, msg=""):
        super().__init__(f"{tipo}: {msg}" if msg else tipo)
        self.tipo = tipo
        self.msg = msg


def _contexto(verificar):
    ctx = ssl.create_default_context()
    if not verificar:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


class ClienteHTTP:
    def __init__(self, timeout=10.0, tentativas=2):
        self.timeout = timeout
        self.tentativas = tentativas

    def get(self, url, verificar=True, ler=0):
        erro = None
        for _ in range(self.tentativas):
            try:
                return self._get(url, verificar, ler)
            except ErroConexao as e:
                erro = e
                # so vale tentar de novo se foi coisa de rede
                if e.tipo not in ("timeout", "outro"):
                    break
        raise erro

    def _get(self, url, verificar, ler):
        partes = urlsplit(url)
        caminho = partes.path or "/"
        if partes.query:
            caminho += "?" + partes.query

        if partes.scheme == "https":
            conn = http.client.HTTPSConnection(
                partes.hostname, partes.port, timeout=self.timeout, context=_contexto(verificar)
            )
        else:
            conn = http.client.HTTPConnection(partes.hostname, partes.port, timeout=self.timeout)

        try:
            conn.connect()
            # pega a versao antes do getresponse, porque com Connection: close o sock some
            tls = conn.sock.version() if partes.scheme == "https" else None
            conn.request("GET", caminho, headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,*/*;q=0.8",
                "Connection": "close",
            })
            resp = conn.getresponse()
            headers = {}
            for k, v in resp.getheaders():
                k = k.lower()
                headers[k] = f"{headers[k]}, {v}" if k in headers else v
            corpo = resp.read(ler) if ler else b""
            return Resposta(url=url, status=resp.status, headers=headers, corpo=corpo, tls=tls)
        except ssl.SSLCertVerificationError as e:
            raise ErroConexao("certificado", e.verify_message or str(e)) from e
        except ssl.SSLError as e:
            raise ErroConexao("tls", e.reason or str(e)) from e
        except socket.gaierror as e:
            raise ErroConexao("dns", str(e)) from e
        except ConnectionRefusedError as e:
            raise ErroConexao("recusada") from e
        except TimeoutError as e:
            raise ErroConexao("timeout") from e
        except (OSError, http.client.HTTPException) as e:
            raise ErroConexao("outro", f"{type(e).__name__}: {e}") from e
        finally:
            conn.close()


def seguir(cliente, url, verificar=False, max_saltos=5, ler=0):
    """Segue redirects e devolve a ultima resposta."""
    resp = cliente.get(url, verificar=verificar, ler=ler)
    for _ in range(max_saltos):
        local = resp.headers.get("location")
        if resp.status not in REDIRECTS or not local:
            break
        resp = cliente.get(urljoin(resp.url, local), verificar=verificar, ler=ler)
    return resp


def avaliar_hsts(valor):
    if not valor:
        return Resultado("hsts", FAIL, "sem header Strict-Transport-Security")
    m = re.search(r"max-age\s*=\s*\"?(\d+)", valor, re.I)
    if not m or int(m.group(1)) == 0:
        return Resultado("hsts", FAIL, "max-age ausente ou zero")
    idade = int(m.group(1))
    if idade >= HSTS_MINIMO:
        return Resultado("hsts", PASS, f"max-age={idade}")
    return Resultado("hsts", WARN, f"max-age={idade} (menos de 1 ano)")


def avaliar_headers(headers):
    # header duplicado (proxy + aplicacao) chega como "nosniff, nosniff"
    nosniff = "nosniff" in headers.get("x-content-type-options", "").lower()
    csp = headers.get("content-security-policy", "").lower()
    frame = "x-frame-options" in headers or "frame-ancestors" in csp

    if nosniff and frame:
        return Resultado("headers", PASS, "nosniff e anti-clickjacking")
    if nosniff or frame:
        falta = "anti-clickjacking" if nosniff else "X-Content-Type-Options"
        return Resultado("headers", WARN, f"falta {falta}")
    return Resultado("headers", FAIL, "sem X-Content-Type-Options nem anti-clickjacking")


def avaliar_security_txt(resp):
    tipo = resp.headers.get("content-type", "").lower()
    if resp.status != 200:
        return Resultado("security_txt", FAIL, f"nao encontrado (HTTP {resp.status})")
    if "text/html" in tipo:
        # muito site devolve a home com 200 pra qualquer caminho
        return Resultado("security_txt", FAIL, "caminho devolve uma pagina HTML")
    texto = resp.corpo.decode("utf-8", "replace").lower()
    if any(linha.strip().startswith("contact:") for linha in texto.splitlines()):
        return Resultado("security_txt", PASS, "arquivo com Contact")
    return Resultado("security_txt", FAIL, "arquivo sem campo Contact")


def _checar_redirect(host, cliente, tem_https):
    url = f"http://{host}/"
    try:
        resp = cliente.get(url, verificar=False)
        for _ in range(5):
            local = resp.headers.get("location")
            if resp.status not in REDIRECTS or not local:
                break
            url = urljoin(url, local)
            if url.startswith("https://"):
                return Resultado("redirect", PASS, f"redireciona para {url}"), True
            resp = cliente.get(url, verificar=False)
    except ErroConexao as e:
        # porta 80 fechada/filtrada nao e problema se o HTTPS funciona
        if tem_https and e.tipo in ("recusada", "timeout"):
            return Resultado("redirect", PASS, "porta 80 nao responde, so HTTPS"), False
        if e.tipo in ("recusada", "dns"):
            return Resultado("redirect", FAIL, f"HTTP indisponivel ({e.tipo})"), False
        return Resultado("redirect", ERROR, str(e)), False

    if 200 <= resp.status < 300:
        return Resultado("redirect", FAIL, "site responde em HTTP sem redirecionar"), True
    return Resultado("redirect", FAIL, f"HTTP nao redireciona (HTTP {resp.status})"), True


def checar_web(host, cliente):
    """Roda todos os checks web. Devolve (acessivel, lista de Resultado)."""
    resultados = []
    resp_https = None
    cert_ok = False
    erro_https = None

    try:
        resp_https = cliente.get(f"https://{host}/", verificar=True)
        cert_ok = True
        resultados.append(Resultado("https", PASS, "certificado valido"))
    except ErroConexao as e:
        erro_https = e
        if e.tipo == "certificado":
            resultados.append(Resultado("https", FAIL, f"certificado invalido: {e.msg}"))
            try:
                resp_https = cliente.get(f"https://{host}/", verificar=False)
            except ErroConexao:
                pass
        elif e.tipo in ("recusada", "dns"):
            resultados.append(Resultado("https", FAIL, "nao responde em HTTPS"))
        elif e.tipo == "tls":
            resultados.append(Resultado("https", FAIL, f"falha no handshake TLS: {e.msg}"))
        else:
            resultados.append(Resultado("https", ERROR, str(e)))

    redirect, http_respondeu = _checar_redirect(host, cliente, resp_https is not None)
    resultados.append(redirect)

    # TLS
    if resp_https is not None:
        if resp_https.tls in TLS_OK:
            resultados.append(Resultado("tls", PASS, resp_https.tls))
        else:
            resultados.append(Resultado("tls", FAIL, f"negociou {resp_https.tls}"))
    elif erro_https is not None and erro_https.tipo == "tls":
        # o cliente exige TLS 1.2+, entao handshake falho geralmente e servidor antigo
        resultados.append(Resultado("tls", FAIL, "nao negocia TLS 1.2 ou superior"))
    elif erro_https is not None and erro_https.tipo in ("timeout", "outro"):
        resultados.append(Resultado("tls", ERROR, str(erro_https)))
    else:
        resultados.append(Resultado("tls", FAIL, "sem HTTPS"))

    # HSTS so conta com certificado valido, navegador ignora no resto
    if cert_ok:
        resultados.append(avaliar_hsts(resp_https.headers.get("strict-transport-security")))
    else:
        resultados.append(Resultado("hsts", FAIL, "sem HTTPS valido"))

    # headers da pagina final, depois dos redirects
    base = f"https://{host}/" if resp_https is not None else f"http://{host}/"
    try:
        final = seguir(cliente, base)
        resultados.append(avaliar_headers(final.headers))
    except ErroConexao as e:
        resultados.append(Resultado("headers", ERROR, str(e)))

    if resp_https is not None:
        try:
            resp = seguir(cliente, f"https://{host}/.well-known/security.txt", max_saltos=3, ler=32768)
            resultados.append(avaliar_security_txt(resp))
        except ErroConexao as e:
            resultados.append(Resultado("security_txt", ERROR, str(e)))
    else:
        resultados.append(Resultado("security_txt", FAIL, "sem HTTPS"))

    acessivel = resp_https is not None or http_respondeu
    return acessivel, resultados
