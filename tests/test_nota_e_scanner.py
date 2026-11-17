from farol.checks import FAIL, PASS, WARN, Resultado
from farol.checks.web import ErroConexao
from farol.dominios import Entidade, dominio_email, normalizar_host, uf_do_ibge
from farol.nota import PESOS, calcular_nota, conceito
from farol.resumo import gerar_markdown, linhas_revisao
from farol.scanner import avaliar, varrer
from tests.fakes import FakeCliente, FakeResolver, resp


def test_nota_maxima_e_minima():
    assert calcular_nota([Resultado(c, PASS) for c in PESOS]) == 100.0
    assert calcular_nota([Resultado(c, FAIL) for c in PESOS]) == 0.0


def test_warn_vale_metade():
    # so dmarc (peso 3) em warn, o resto falhou
    resultados = [Resultado(c, FAIL) for c in PESOS if c != "dmarc"] + [Resultado("dmarc", WARN)]
    assert calcular_nota(resultados) == round(100 * 1.5 / sum(PESOS.values()), 1)


def test_conceitos():
    assert conceito(100) == "A"
    assert conceito(90) == "A"
    assert conceito(89.9) == "B"
    assert conceito(55) == "C"
    assert conceito(35) == "D"
    assert conceito(34.9) == "F"


def test_dominios():
    assert normalizar_host("https://WWW.Recife.PE.gov.br/portal/") == "www.recife.pe.gov.br"
    assert normalizar_host("campinas.sp.gov.br") == "campinas.sp.gov.br"
    assert dominio_email("www.recife.pe.gov.br") == "recife.pe.gov.br"
    assert uf_do_ibge("2611606") == "PE"
    assert uf_do_ibge("5300108") == "DF"


def _ambiente():
    host = "www.cidade.sp.gov.br"
    https, http = f"https://{host}/", f"http://{host}/"
    resolver = FakeResolver(
        txt={
            "cidade.sp.gov.br": ["v=spf1 mx -all"],
            "_dmarc.cidade.sp.gov.br": ["v=DMARC1; p=none"],
        },
        enderecos={host: (True, False)},
    )
    cliente = FakeCliente({
        https: resp(https, headers={"x-content-type-options": "nosniff"}),
        http: resp(http, status=301, headers={"location": https}),
    })
    return Entidade("3509502", "Cidade", "SP", host), resolver, cliente


def test_avaliar_dominio():
    ent, resolver, cliente = _ambiente()
    r = avaliar(ent, resolver, cliente)

    assert r["acessivel"]
    assert set(r["checks"]) == set(PESOS)
    assert r["checks"]["dmarc"]["status"] == WARN
    assert r["checks"]["dnssec"]["status"] == FAIL
    assert 0 < r["nota"] < 100


def test_dominio_que_nao_resolve_fica_sem_nota():
    ent = Entidade("3509502", "Cidade", "SP", "fora.sp.gov.br")
    r = avaliar(ent, FakeResolver(), FakeCliente({}))
    assert not r["acessivel"]
    assert r["nota"] is None
    assert set(r["checks"]) == set(PESOS)


def test_varredura_e_resumo():
    ent, resolver, cliente = _ambiente()
    fora = Entidade("2611606", "Outra", "PE", "fora.pe.gov.br")
    dados = varrer([ent, fora], lambda: resolver, cliente, workers=2)

    assert dados["total"] == 2
    md = gerar_markdown(dados)
    assert "| 1 | SP |" in md
    assert "1 não responderam" in md
    # o dominio que nao resolve gera erro em todos os checks web
    assert "| https | 1 | dominio nao resolve |" in md


def test_usa_dominio_sem_www_quando_o_cadastrado_nao_existe():
    host = "cidade.sp.gov.br"
    resolver = FakeResolver(enderecos={host: (True, True)})
    cliente = FakeCliente({f"https://{host}/": resp(f"https://{host}/")})
    r = avaliar(Entidade("3509502", "Cidade", "SP", "www." + host), resolver, cliente)

    assert r["dominio"] == host
    assert r["dominio_wikidata"] == "www." + host
    assert "dominio_alternativo" in r["avisos"]
    assert r["acessivel"]
    assert r["ranking"]


def test_dominio_fora_do_gov_br_sai_do_ranking():
    host = "www.associacao.org.br"
    resolver = FakeResolver(enderecos={host: (True, False)})
    cliente = FakeCliente({f"https://{host}/": resp(f"https://{host}/")})
    r = avaliar(Entidade("1301159", "Careiro", "AM", host), resolver, cliente)

    assert r["acessivel"]
    assert r["nota"] is not None
    assert not r["ranking"]
    assert "fora_do_gov_br" in r["avisos"]


def test_dominio_repetido_vira_compartilhado():
    ent, resolver, cliente = _ambiente()
    outro = Entidade("3509601", "Vizinha", "SP", ent.dominio)
    dados = varrer([ent, outro], lambda: resolver, cliente, workers=2)

    for r in dados["resultados"]:
        assert "dominio_compartilhado" in r["avisos"]
        assert not r["ranking"]


def test_linhas_de_revisao():
    ent, resolver, cliente = _ambiente()
    fora = Entidade("2611606", "Outra", "PE", "fora.pe.gov.br")
    dados = varrer([ent, fora], lambda: resolver, cliente, workers=2)

    revisao = linhas_revisao(dados)
    assert len(revisao) == 1
    assert revisao[0]["ibge"] == "2611606"
    assert "não existe" in revisao[0]["motivo"]


def test_coordenadas_vao_pro_resultado():
    ent, resolver, cliente = _ambiente()
    com_coord = Entidade(ent.ibge, ent.municipio, ent.uf, ent.dominio, lat="-22.9056", lon="-47.0608")
    r = avaliar(com_coord, resolver, cliente)
    assert (r["lat"], r["lon"]) == (-22.9056, -47.0608)

    sem = avaliar(ent, resolver, cliente)
    assert sem["lat"] is None


def test_item_nao_verificado_nao_vale_zero():
    # tudo certo, mas o DMARC deu timeout do nosso lado: a nota nao pode cair por isso
    resultados = [Resultado(c, PASS) for c in PESOS if c != "dmarc"] + [Resultado("dmarc", "error", "LifetimeTimeout")]
    assert calcular_nota(resultados) == 100.0


def test_sem_nota_quando_falta_verificar_demais():
    resultados = [Resultado(c, "error", "timeout") for c in PESOS]
    resultados[0] = Resultado("https", PASS)
    assert calcular_nota(resultados) is None


def test_repescagem_recupera_quem_deu_timeout():
    ent, resolver, cliente = _ambiente()

    class ClienteInstavel(FakeCliente):
        def get(self, url, verificar=True, ler=0):
            raise ErroConexao("timeout")

    instavel = ClienteInstavel({})
    dados = varrer([ent], lambda: resolver, instavel, workers=1, cliente_lento=cliente)
    r = dados["resultados"][0]
    assert dados["repescagem"] == {"tentados": 1, "recuperados": 1, "fora_do_prazo": 0}
    assert r["checks"]["https"]["status"] != "error"
    assert r["acessivel"]


def test_repescagem_respeita_o_prazo():
    import time

    ent, resolver, cliente = _ambiente()

    class ClienteInstavel(FakeCliente):
        def get(self, url, verificar=True, ler=0):
            raise ErroConexao("timeout")

    class ClienteTravado(FakeCliente):
        def get(self, url, verificar=True, ler=0):
            time.sleep(0.6)
            return super().get(url, verificar, ler)

    inicio = time.monotonic()
    dados = varrer([ent], lambda: resolver, ClienteInstavel({}), workers=1, cliente_lento=ClienteTravado(cliente.rotas), prazo_repescagem=0.1)
    assert time.monotonic() - inicio < 0.5
    # o resultado da primeira passada fica valendo
    assert dados["repescagem"] == {"tentados": 1, "recuperados": 0, "fora_do_prazo": 1}
    assert dados["resultados"][0]["checks"]["https"]["status"] == "error"


def test_limite_por_servidor():
    import threading
    import time

    from farol.scanner import LimitePorServidor

    limite = LimitePorServidor(por_ip=2)
    ativos, maximo = [0], [0]
    trava = threading.Lock()

    def usa():
        with limite("10.0.0.1"):
            with trava:
                ativos[0] += 1
                maximo[0] = max(maximo[0], ativos[0])
            time.sleep(0.02)
            with trava:
                ativos[0] -= 1

    threads = [threading.Thread(target=usa) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert maximo[0] == 2


class _ResolverPorIp(FakeResolver):
    """lento-N.x.gov.br fica no IP 10.0.0.9, o resto cada um no seu IP."""

    def endereco(self, nome):
        ip = "10.0.0.9" if nome.startswith("lento") else f"10.1.{len(nome)}.{sum(map(ord, nome)) % 250}"
        return True, False, [ip]


class _ClienteMedido(FakeCliente):
    """Responde 200 pra tudo, demora nos hosts 'lento' e mede quantos rodam juntos por servidor."""

    def __init__(self, espera=0.05):
        super().__init__({})
        import threading

        self.espera = espera
        self.trava = threading.Lock()
        self.ativos, self.maximo, self.terminou = {}, {}, {}

    def get(self, url, verificar=True, ler=0):
        import time

        host = url.split("/")[2]
        chave = "lento" if host.startswith("lento") else host
        with self.trava:
            self.ativos[chave] = self.ativos.get(chave, 0) + 1
            self.maximo[chave] = max(self.maximo.get(chave, 0), self.ativos[chave])
        try:
            if chave == "lento":
                time.sleep(self.espera)
            return resp(url)
        finally:
            with self.trava:
                self.ativos[chave] -= 1
                self.terminou[host] = time.monotonic()


def _entidades(lentos, rapidos):
    ents = [Entidade(f"35{i:05d}", f"Lenta {i}", "SP", f"lento-{i}.sp.gov.br") for i in range(lentos)]
    ents += [Entidade(f"31{i:05d}", f"Rapida {i}", "MG", f"rapida-{i}.mg.gov.br") for i in range(rapidos)]
    return ents


def test_servidor_lento_nao_trava_os_outros():
    # 20 cidades no mesmo servidor lento e 20 em servidores normais, com 4 threads.
    # antes as 4 threads ficavam presas esperando a vez do servidor lento
    import time

    cliente = _ClienteMedido(espera=0.03)
    inicio = time.monotonic()
    dados = varrer(_entidades(20, 20), _ResolverPorIp, cliente, workers=4, por_ip=2)

    assert dados["total"] == 40
    assert cliente.maximo["lento"] <= 2
    fim_rapidas = max(t for h, t in cliente.terminou.items() if h.startswith("rapida"))
    fim_lentas = max(t for h, t in cliente.terminou.items() if h.startswith("lento"))
    # as rapidas terminam bem antes da fila do servidor lento acabar
    assert fim_rapidas - inicio < 0.3 * (fim_lentas - inicio)


def test_prazo_da_varredura_deixa_sem_nota_e_nao_some_com_ninguem():
    cliente = _ClienteMedido(espera=0.2)
    dados = varrer(_entidades(10, 3), _ResolverPorIp, cliente, workers=2, por_ip=1, prazo=0.3)

    assert dados["total"] == 13  # ninguem some do resultado
    assert dados["sem_visita_por_prazo"] > 0
    assert dados["repescagem"]["tentados"] == 0  # sem tempo nao tem repescagem
    sem_visita = [r for r in dados["resultados"] if r["checks"]["https"]["detalhe"].startswith("prazo")]
    assert len(sem_visita) == dados["sem_visita_por_prazo"]
    for r in sem_visita:
        assert r["nota"] is None and "verificacao_incompleta" in r["avisos"]
        # o dns foi feito mesmo assim
        assert r["checks"]["spf"]["status"] != "error" or "prazo" not in r["checks"]["spf"]["detalhe"]


class _ClienteMorto(FakeCliente):
    """Servidor que nao responde nada (timeout em tudo)."""

    def __init__(self):
        super().__init__({})
        self.hosts = set()

    def get(self, url, verificar=True, ler=0):
        self.hosts.add(url.split("/")[2])
        raise ErroConexao("timeout")


def test_servidor_mudo_passa_a_ser_sondado():
    principal, sondagem = _ClienteMorto(), _ClienteMorto()
    dados = varrer(_entidades(10, 0), _ResolverPorIp, principal, workers=1, por_ip=1, sondagem=sondagem, cliente_lento=FakeCliente({}))

    assert dados["total"] == 10
    # as 3 primeiras levam a visita completa; as outras so a sondagem rapida
    assert len(principal.hosts) == 3
    assert len(sondagem.hosts) == 7
    assert not any(r["acessivel"] for r in dados["resultados"])


def test_sondagem_que_responde_faz_a_visita_completa():
    principal = _ClienteMedido()
    sondagem = _ClienteMedido()
    # todos no mesmo servidor, que responde normalmente: sondagem nunca entra
    dados = varrer(_entidades(6, 0), _ResolverPorIp, principal, workers=1, por_ip=1, sondagem=sondagem)
    assert all(r["acessivel"] for r in dados["resultados"])
    assert not sondagem.terminou


class _ResolverDemorado(_ResolverPorIp):
    """O DNS de 'lerdo-*' demora; os outros respondem na hora."""

    def __init__(self, espera=0.5):
        super().__init__()
        self.espera = espera

    def endereco(self, nome):
        import time

        if nome.startswith("lerdo"):
            time.sleep(self.espera)
        return super().endereco(nome)


def test_dns_lento_nao_segura_as_visitas_das_outras():
    import time

    ents = _entidades(0, 6) + [Entidade("3300001", "Lerda", "RJ", "lerdo.rj.gov.br")]
    cliente = _ClienteMedido()
    inicio = time.monotonic()
    dados = varrer(ents, lambda: _ResolverDemorado(0.5), cliente, workers=4)
    assert dados["total"] == 7
    fim_rapidas = max(t for h, t in cliente.terminou.items() if h.startswith("rapida"))
    assert fim_rapidas - inicio < 0.4


def test_prazo_com_dns_pendente_nao_some_com_a_cidade():
    ents = _entidades(0, 2) + [Entidade("3300001", "Lerda", "RJ", "lerdo.rj.gov.br")]
    dados = varrer(ents, lambda: _ResolverDemorado(1.0), _ClienteMedido(), workers=4, prazo=0.3)
    assert dados["total"] == 3
    lerda = next(r for r in dados["resultados"] if r["ibge"] == "3300001")
    assert lerda["nota"] is None and "verificacao_incompleta" in lerda["avisos"]
    assert dados["sem_visita_por_prazo"] == 1


def test_zona_que_nao_responde_nao_gasta_mais_consultas():
    from farol.checks.dns import ErroDNS
    from farol.scanner import preparar

    class Mudo(FakeResolver):
        def __init__(self):
            super().__init__()
            self.consultas = []

        def endereco(self, nome):
            self.consultas.append(("A", nome))
            raise ErroDNS("LifetimeTimeout: o DNS de x nao respondeu a tempo")

        def txt(self, nome):
            self.consultas.append(("TXT", nome))
            return []

        def caa(self, nome):
            self.consultas.append(("CAA", nome))
            return []

    resolver = Mudo()
    prep = preparar(Entidade("3509502", "Cidade", "SP", "www.cidade.sp.gov.br"), resolver)
    assert resolver.consultas == [("A", "www.cidade.sp.gov.br")]
    assert all(r.status == "error" for r in prep.dns)


def test_repescagem_do_dns_nao_refaz_a_visita():
    from farol.checks.dns import ErroDNS

    ent, _, cliente = _ambiente()

    class Engasgado(FakeResolver):
        # o primeiro TXT da cidade estoura o tempo, os seguintes respondem
        falhou = []

        def txt(self, nome):
            if nome == "cidade.sp.gov.br" and not Engasgado.falhou:
                Engasgado.falhou.append(nome)
                raise ErroDNS("LifetimeTimeout: o DNS de cidade.sp.gov.br nao respondeu a tempo")
            return super().txt(nome)

    def novo():
        return Engasgado(
            txt={"cidade.sp.gov.br": ["v=spf1 mx -all"], "_dmarc.cidade.sp.gov.br": ["v=DMARC1; p=none"]},
            enderecos={ent.dominio: (True, False)},
        )

    dados = varrer([ent], novo, cliente, workers=1)
    r = dados["resultados"][0]
    assert dados["repescagem"]["recuperados"] == 1
    assert r["checks"]["spf"]["status"] == "pass"
    # a home foi visitada uma vez so (https), sem repetir a visita inteira
    assert cliente.chamadas.count((f"https://{ent.dominio}/", True)) == 1
