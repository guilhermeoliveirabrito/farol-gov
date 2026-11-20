"""Checks web: HTTPS, redirecionamento, TLS, HSTS, headers, conteúdo misto, cookies e security.txt.

Usa só a biblioteca padrão. Tudo aqui é GET simples, igual um navegador faria.
A única exceção é o teste de TLS antigo, que é só um handshake (sem requisição HTTP),
o mesmo que ferramentas como o SSL Labs fazem.
"""
import http.client
import re
import socket
import ssl
import time
import warnings
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit

from farol import USER_AGENT

from . import ERROR, FAIL, PASS, WARN, Resultado

REDIRECTS = (301, 302, 303, 307, 308)
TLS_OK = ("TLSv1.2", "TLSv1.3")
HSTS_MINIMO = 31536000  # 1 ano
CERT_DIAS_AVISO = 14
CORPO_MAXIMO = 512 * 1024  # o suficiente pra achar recurso http:// no HTML da pagina inicial


@dataclass
class Resposta:
    url: str
    status: int
    headers: dict = field(default_factory=dict)
    corpo: bytes = b""
    tls: str | None = None
    # Set-Cookie fica separado: juntar com virgula quebra a data do Expires
    cookies: list = field(default_factory=list)
    # validade do certificado (epoch), so quando a conexao foi verificada
    expira: float | None = None


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


def _ler_com_prazo(resp, maximo, prazo):
    """Le ate `maximo` bytes, mas para no prazo. O timeout do socket vale por leitura,
    entao um servidor que manda poucos bytes por vez segurava a thread por minutos."""
    blocos, falta = [], maximo
    while falta > 0 and time.monotonic() < prazo:
        bloco = resp.read1(min(65536, falta))
        if not bloco:
            break
        blocos.append(bloco)
        falta -= len(bloco)
    return b"".join(blocos)


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
            # pega versao e certificado antes do getresponse, porque com Connection: close o sock some
            tls = conn.sock.version() if partes.scheme == "https" else None
            expira = None
            if partes.scheme == "https" and verificar:
                cert = conn.sock.getpeercert() or {}
                if cert.get("notAfter"):
                    expira = ssl.cert_time_to_seconds(cert["notAfter"])
            conn.request("GET", caminho, headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,*/*;q=0.8",
                "Connection": "close",
            })
            resp = conn.getresponse()
            headers = {}
            cookies = []
            for k, v in resp.getheaders():
                k = k.lower()
                if k == "set-cookie":
                    cookies.append(v)
                headers[k] = f"{headers[k]}, {v}" if k in headers else v
            corpo = _ler_com_prazo(resp, ler, time.monotonic() + self.timeout * 2) if ler else b""
            return Resposta(url=url, status=resp.status, headers=headers, corpo=corpo, tls=tls, cookies=cookies, expira=expira)
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


    def aceita_tls_antigo(self, host, porta=443):
        """Tenta um handshake oferecendo so TLS 1.0 e 1.1. Devolve a versao aceita ou None.

        Levanta ErroConexao se nao der pra testar (conexao caiu, ou o OpenSSL local sem suporte).
        Esse teste so roda depois do handshake moderno ter funcionado, entao o servidor
        esta no ar: se ele fica mudo diante de um ClientHello TLS 1.0 (firewall/WAF que
        descarta), na pratica nao aceita a versao antiga.
        """
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            # o python avisa que TLSv1 e obsoleto; aqui e justamente o que a gente quer testar
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                ctx.minimum_version = ssl.TLSVersion.TLSv1
                ctx.maximum_version = ssl.TLSVersion.TLSv1_1
            # sem isso o OpenSSL 3 nem tenta as versoes antigas
            ctx.set_ciphers("DEFAULT:@SECLEVEL=0")
        except (ValueError, ssl.SSLError) as e:
            raise ErroConexao("local", f"OpenSSL local sem suporte a TLS antigo: {e}") from e
        # nao precisa esperar o timeout cheio: o servidor ja respondeu ao handshake moderno
        espera = min(self.timeout, 6.0)
        try:
            with socket.create_connection((host, porta), timeout=espera) as sock, ctx.wrap_socket(sock, server_hostname=host) as tls:
                return tls.version()
        except ssl.SSLError as e:
            # NO_PROTOCOLS_AVAILABLE e o OpenSSL daqui se recusando a mandar TLS 1.0; nao e o servidor
            if getattr(e, "reason", None) == "NO_PROTOCOLS_AVAILABLE":
                raise ErroConexao("local", "OpenSSL local nao deixa oferecer TLS 1.0/1.1") from e
            return None
        except ConnectionResetError:
            # muito servidor simplesmente derruba a conexao quando nao aceita a versao
            return None
        except TimeoutError:
            # antes isso virava erro e mandava o dominio pra repescagem, que ficava lentissima
            return None
        except OSError as e:
            raise ErroConexao("outro", f"{type(e).__name__}: {e}") from e


def seguir(cliente, url, verificar=False, max_saltos=5, ler=0, inicio=None):
    """Segue redirects e devolve a ultima resposta. Se `inicio` vier, comeca dele sem baixar de novo."""
    resp = inicio or cliente.get(url, verificar=verificar, ler=ler)
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
        extras = [x for x in ("includeSubDomains", "preload") if x.lower() in valor.lower()]
        return Resultado("hsts", PASS, "; ".join([f"max-age={idade}", *extras]))
    return Resultado("hsts", WARN, f"max-age={idade} (menos de 1 ano)")


def avaliar_headers(headers):
    # header duplicado (proxy + aplicacao) chega como "nosniff, nosniff"
    nosniff = "nosniff" in headers.get("x-content-type-options", "").lower()
    csp = headers.get("content-security-policy", "").lower()
    frame = "x-frame-options" in headers or "frame-ancestors" in csp

    if nosniff and frame:
        extras = [nome for nome, tem in (("CSP", csp), ("Referrer-Policy", "referrer-policy" in headers), ("Permissions-Policy", "permissions-policy" in headers)) if tem]
        return Resultado("headers", PASS, "nosniff e anti-clickjacking" + (", com " + ", ".join(extras) if extras else ""))
    if nosniff or frame:
        falta = "anti-clickjacking" if nosniff else "X-Content-Type-Options"
        return Resultado("headers", WARN, f"falta {falta}")
    return Resultado("headers", FAIL, "sem X-Content-Type-Options nem anti-clickjacking")


# recurso ativo (script, iframe, css) carregado por http:// numa pagina https
ATIVO = re.compile(
    r"<(?:script|iframe|frame|embed|object)\b[^>]*?\s(?:src|data)\s*=\s*[\"']?http://"
    r"|<link\b(?=[^>]*rel\s*=\s*[\"']?stylesheet)[^>]*?\shref\s*=\s*[\"']?http://"
    r"|<form\b[^>]*?\saction\s*=\s*[\"']?http://",
    re.I,
)
# recurso passivo (imagem, audio, video): o navegador carrega mas avisa
PASSIVO = re.compile(r"<(?:img|audio|video|source)\b[^>]*?\ssrc\s*=\s*[\"']?http://", re.I)


def avaliar_conteudo_misto(resp):
    if not resp.url.startswith("https://"):
        return Resultado("conteudo_misto", FAIL, "a pagina final e servida sem HTTPS")
    html = resp.corpo.decode("utf-8", "replace")
    if "<" not in html:
        return Resultado("conteudo_misto", ERROR, "pagina sem HTML pra analisar")
    ativos = len(ATIVO.findall(html))
    passivos = len(PASSIVO.findall(html))
    if ativos:
        return Resultado("conteudo_misto", FAIL, f"{ativos} script(s), iframe(s) ou formulario(s) por http://")
    if passivos:
        return Resultado("conteudo_misto", WARN, f"{passivos} imagem(ns) ou midia(s) por http://")
    return Resultado("conteudo_misto", PASS, "nenhum recurso carregado sem criptografia")


def _atributos_cookie(cookie):
    nome = cookie.split("=", 1)[0].strip()
    attrs = {a.strip().split("=", 1)[0].lower() for a in cookie.split(";")[1:]}
    return nome, attrs


def avaliar_cookies(cookies):
    if not cookies:
        return Resultado("cookies", PASS, "a pagina inicial nao define cookies")
    sem_secure, sem_httponly, sem_samesite = [], [], []
    for c in cookies:
        nome, attrs = _atributos_cookie(c)
        if "secure" not in attrs:
            sem_secure.append(nome)
        if "httponly" not in attrs:
            sem_httponly.append(nome)
        if "samesite" not in attrs:
            sem_samesite.append(nome)
    if sem_secure:
        return Resultado("cookies", FAIL, f"{len(sem_secure)} de {len(cookies)} cookie(s) sem Secure: {', '.join(sem_secure[:3])}")
    if sem_httponly:
        return Resultado("cookies", WARN, f"{len(sem_httponly)} de {len(cookies)} cookie(s) sem HttpOnly")
    detalhe = f"{len(cookies)} cookie(s) com Secure e HttpOnly"
    # SameSite protege contra outro site disparar acao em nome de quem esta logado (CSRF)
    if sem_samesite:
        detalhe += f"; {len(sem_samesite)} sem SameSite"
    return Resultado("cookies", PASS, detalhe)


def avaliar_validade(expira, agora=None):
    """Complementa o check de HTTPS: certificado valido mas vencendo logo vira parcial."""
    if expira is None:
        return Resultado("https", PASS, "certificado valido")
    dias = round((expira - (agora or time.time())) / 86400)
    if dias < CERT_DIAS_AVISO:
        return Resultado("https", WARN, f"certificado valido, mas vence em {dias} dia(s)")
    return Resultado("https", PASS, f"certificado valido por mais {dias} dias")


def avaliar_security_txt(resp):
    tipo = resp.headers.get("content-type", "").lower()
    if resp.status != 200:
        return Resultado("security_txt", FAIL, f"nao encontrado (HTTP {resp.status})")
    if "text/html" in tipo:
        # muito site devolve a home com 200 pra qualquer caminho
        return Resultado("security_txt", FAIL, "caminho devolve uma pagina HTML")
    texto = resp.corpo.decode("utf-8", "replace").lower()
    linhas = [linha.strip() for linha in texto.splitlines()]
    if any(linha.startswith("contact:") for linha in linhas):
        # a RFC 9116 exige Expires, pra ninguem confiar num contato abandonado
        if any(linha.startswith("expires:") for linha in linhas):
            return Resultado("security_txt", PASS, "arquivo com Contact e Expires")
        return Resultado("security_txt", PASS, "arquivo com Contact, sem Expires")
    return Resultado("security_txt", FAIL, "arquivo sem campo Contact")


# "Apache/2.4.29", "PHP/7.4.3", "nginx/1.18.0", "Microsoft-IIS/10.0"
COM_VERSAO = re.compile(r"[a-z][\w.!-]*[/ ]v?\d+(?:\.\d+)+", re.I)
GERADOR = re.compile(r"<meta[^>]+name\s*=\s*[\"']generator[\"'][^>]*content\s*=\s*[\"']([^\"']+)", re.I)
GERADOR_INVERTIDO = re.compile(r"<meta[^>]+content\s*=\s*[\"']([^\"']+)[\"'][^>]*name\s*=\s*[\"']generator", re.I)


def avaliar_versao_exposta(resp):
    """Mostrar a versao exata do servidor ou do sistema do site entrega pro atacante a
    lista de falhas conhecidas daquela versao. O nome sozinho ("nginx") e bem menos grave."""
    html = resp.corpo.decode("utf-8", "replace") if resp.corpo else ""
    fontes = [resp.headers.get(h, "") for h in ("server", "x-powered-by", "x-aspnet-version", "x-aspnetmvc-version")]
    gerador = GERADOR.search(html) or GERADOR_INVERTIDO.search(html)
    if gerador:
        fontes.append(gerador.group(1))
    if resp.headers.get("x-aspnet-version"):
        fontes.append("ASP.NET/" + resp.headers["x-aspnet-version"])
    versoes = []
    for f in fontes:
        for m in COM_VERSAO.finditer(f):
            if m.group(0) not in versoes:
                versoes.append(m.group(0))
    if versoes:
        return Resultado("versao_exposta", FAIL, "mostra a versao: " + ", ".join(versoes[:3]))
    nomes = [f.split("/")[0].strip() for f in fontes if f.strip()]
    if nomes:
        return Resultado("versao_exposta", PASS, "mostra so o nome: " + ", ".join(dict.fromkeys(nomes[:3])))
    return Resultado("versao_exposta", PASS, "nao mostra o software")


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

    # o corpo ja vem nessa primeira requisicao, pra nao precisar baixar a pagina de novo
    try:
        resp_https = cliente.get(f"https://{host}/", verificar=True, ler=CORPO_MAXIMO)
        cert_ok = True
        resultados.append(avaliar_validade(resp_https.expira))
    except ErroConexao as e:
        erro_https = e
        if e.tipo == "certificado":
            resultados.append(Resultado("https", FAIL, f"certificado invalido: {e.msg}"))
            try:
                resp_https = cliente.get(f"https://{host}/", verificar=False, ler=CORPO_MAXIMO)
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

    # TLS negociado
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

    # TLS antigo: o servidor ainda aceita 1.0 ou 1.1?
    if resp_https is not None or (erro_https is not None and erro_https.tipo == "tls"):
        try:
            antigo = cliente.aceita_tls_antigo(host)
            if antigo:
                resultados.append(Resultado("tls_antigo", FAIL, f"ainda aceita {antigo}"))
            else:
                resultados.append(Resultado("tls_antigo", PASS, "recusa TLS 1.0 e 1.1"))
        except ErroConexao as e:
            resultados.append(Resultado("tls_antigo", ERROR, str(e)))
    elif erro_https is not None and erro_https.tipo in ("timeout", "outro"):
        resultados.append(Resultado("tls_antigo", ERROR, str(erro_https)))
    else:
        resultados.append(Resultado("tls_antigo", FAIL, "sem HTTPS"))

    # HSTS so conta com certificado valido, navegador ignora no resto
    if cert_ok:
        resultados.append(avaliar_hsts(resp_https.headers.get("strict-transport-security")))
    else:
        resultados.append(Resultado("hsts", FAIL, "sem HTTPS valido"))

    # pagina final, depois dos redirects (reaproveita a resposta https quando ela ja e a final)
    try:
        if resp_https is None and not http_respondeu and erro_https is not None and redirect.status == ERROR:
            # nem https nem http responderam: tentar a home pela terceira vez so gasta tempo
            raise erro_https
        if resp_https is not None:
            final = seguir(cliente, None, ler=CORPO_MAXIMO, inicio=resp_https)
        else:
            final = seguir(cliente, f"http://{host}/", ler=CORPO_MAXIMO)
        resultados.append(avaliar_headers(final.headers))
        resultados.append(avaliar_conteudo_misto(final))
        cookies = (resp_https.cookies if resp_https is not None else []) + (final.cookies if final is not resp_https else [])
        resultados.append(avaliar_cookies(cookies))
        resultados.append(avaliar_versao_exposta(final))
    except ErroConexao as e:
        for nome in ("headers", "conteudo_misto", "cookies", "versao_exposta"):
            resultados.append(Resultado(nome, ERROR, str(e)))

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
