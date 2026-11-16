from farol.checks.dns import ErroDNS
from farol.checks.web import ErroConexao, Resposta


class FakeResolver:
    def __init__(self, txt=None, enderecos=None, quebrados=(), caa=None):
        self._txt = txt or {}
        # host -> (existe, ad)
        self._end = enderecos or {}
        self._quebrados = set(quebrados)
        self._caa = caa or {}

    def txt(self, nome):
        if nome in self._quebrados:
            raise ErroDNS("SERVFAIL")
        return self._txt.get(nome, [])

    def endereco(self, nome):
        if nome in self._quebrados:
            raise ErroDNS("SERVFAIL")
        existe, ad = self._end.get(nome, (False, False))
        return existe, ad, ["10.0.0.1"] if existe else []

    def caa(self, nome):
        if nome in self._quebrados:
            raise ErroDNS("LifetimeTimeout: demorou")
        return self._caa.get(nome, [])


class FakeCliente:
    """rotas: {url: Resposta | ErroConexao} ou {(url, verificar): ...}"""

    def __init__(self, rotas, tls_antigo=None):
        self.rotas = rotas
        self.chamadas = []
        # None = recusa TLS antigo; "TLSv1.1" = aceita; ErroConexao = nao deu pra testar
        self.tls_antigo = tls_antigo

    def aceita_tls_antigo(self, host, porta=443):
        if isinstance(self.tls_antigo, ErroConexao):
            raise self.tls_antigo
        return self.tls_antigo

    def get(self, url, verificar=True, ler=0):
        self.chamadas.append((url, verificar))
        alvo = self.rotas.get((url, verificar), self.rotas.get(url))
        if alvo is None:
            raise ErroConexao("recusada")
        if isinstance(alvo, ErroConexao):
            raise alvo
        return alvo


def resp(url, status=200, headers=None, corpo=b"<html></html>", tls="TLSv1.3", cookies=None, expira=None):
    return Resposta(url=url, status=status, headers=headers or {}, corpo=corpo, tls=tls, cookies=cookies or [], expira=expira)
