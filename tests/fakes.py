from farol.checks.dns import ErroDNS
from farol.checks.web import ErroConexao, Resposta


class FakeResolver:
    def __init__(self, txt=None, enderecos=None, quebrados=()):
        self._txt = txt or {}
        # host -> (existe, ad)
        self._end = enderecos or {}
        self._quebrados = set(quebrados)

    def txt(self, nome):
        if nome in self._quebrados:
            raise ErroDNS("SERVFAIL")
        return self._txt.get(nome, [])

    def endereco(self, nome):
        if nome in self._quebrados:
            raise ErroDNS("SERVFAIL")
        return self._end.get(nome, (False, False))


class FakeCliente:
    """rotas: {url: Resposta | ErroConexao} ou {(url, verificar): ...}"""

    def __init__(self, rotas):
        self.rotas = rotas
        self.chamadas = []

    def get(self, url, verificar=True, ler=0):
        self.chamadas.append((url, verificar))
        alvo = self.rotas.get((url, verificar), self.rotas.get(url))
        if alvo is None:
            raise ErroConexao("recusada")
        if isinstance(alvo, ErroConexao):
            raise alvo
        return alvo


def resp(url, status=200, headers=None, corpo=b"", tls="TLSv1.3"):
    return Resposta(url=url, status=status, headers=headers or {}, corpo=corpo, tls=tls)
