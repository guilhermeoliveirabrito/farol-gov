# farol-gov

**Observatório aberto da segurança dos sites e e-mails do governo brasileiro.**

**[Ver o ranking →](https://guilhermeoliveirabrito.github.io/farol-gov/)** · [English version](README.en.md)

O farol-gov verifica, toda semana, se os domínios de prefeituras, governos estaduais e órgãos públicos seguem o básico de segurança na internet: HTTPS de verdade, TLS atualizado, DNSSEC e proteção contra e-mails falsos (SPF e DMARC). O resultado vira um ranking por estado e município, com os dados abertos para quem quiser analisar.

## Por que isso importa

Site de prefeitura não é só vitrine. É ali que o cidadão emite boleto de IPTU, consulta nota fiscal, faz cadastro e às vezes digita senha. E o domínio `.gov.br` é exatamente o que golpistas querem imitar em e-mails de phishing.

Em 2019 um levantamento da DigiCert apontou que [47% dos domínios .gov do Brasil não usavam HTTPS](https://tecnoblog.net/315418/dominios-gov-brasil-nao-usam-https-criptografia/). Desde então ninguém acompanha isso de forma contínua e pública. A ideia aqui é essa: medir sempre, publicar tudo e deixar fácil de ver a evolução.

## O que é verificado

| Check | O que olha | Por que importa |
|---|---|---|
| `https` | O site responde em HTTPS com certificado válido (e que não vence nos próximos 14 dias) | Sem isso, dados de formulário trafegam em texto puro |
| `redirect` | `http://` redireciona para `https://` | Quem digita o endereço sem `https` continua desprotegido |
| `tls` | Versão negociada é TLS 1.2 ou 1.3 | TLS 1.0 e 1.1 estão obsoletos ([RFC 8996](https://www.rfc-editor.org/rfc/rfc8996)) |
| `tls_antigo` | O servidor recusa TLS 1.0 e 1.1 quando alguém pede | Impede que um atacante force a versão mais fraca |
| `hsts` | Header `Strict-Transport-Security` com pelo menos 1 ano | Impede downgrade para HTTP |
| `headers` | `X-Content-Type-Options` e proteção contra clickjacking | Proteções baratas que evitam ataques comuns |
| `conteudo_misto` | A página em HTTPS não carrega scripts ou imagens por `http://` | Um script sem criptografia pode ser trocado e alterar a página |
| `cookies` | Cookies com `Secure` e `HttpOnly` | Protege a sessão de quem faz login no site |
| `security_txt` | Existe `/.well-known/security.txt` com contato | Dá um canal para reportar falhas ([RFC 9116](https://www.rfc-editor.org/rfc/rfc9116)) |
| `dnssec` | Respostas DNS do domínio são validadas | Dificulta sequestro de DNS |
| `caa` | Registro CAA dizendo quem pode emitir certificado | Impede certificado falso emitido por outra autoridade |
| `spf` | Registro SPF que não aceita qualquer remetente | Primeira barreira contra e-mail falso |
| `dmarc` | Política DMARC `quarantine` ou `reject` | Sem isso, qualquer um manda e-mail "da prefeitura" |

Os pesos de cada item e o cálculo da nota estão em [docs/metodologia.md](docs/metodologia.md). Se você administra algum desses sites, o [guia de correção](docs/como-corrigir.md) mostra o que fazer em cada item.

## O que **não** é feito

Todas as verificações são passivas: consultas DNS públicas, um handshake TLS e uma requisição `GET` na página inicial, igual a qualquer navegador. Não há varredura de portas, teste de vulnerabilidade, força bruta nem acesso a áreas restritas. Mais detalhes em [docs/etica.md](docs/etica.md).

## Rodando localmente

```bash
git clone https://github.com/guilhermeoliveirabrito/farol-gov
cd farol-gov
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# verificar um domínio
farol check www.recife.pe.gov.br

# atualizar a lista de domínios a partir do Wikidata
python scripts/coletar_dominios.py

# rodar a varredura completa
farol scan data/dominios.csv -o data/resultados/latest.json
farol resumo data/resultados/latest.json --historico data/historico
farol arquivar data/resultados/latest.json   # guarda a semana no histórico
```

### Vendo a página localmente

```bash
python scripts/montar_site.py          # monta _site/ com os dados de data/
python -m http.server -d _site 8000    # abre em http://localhost:8000
```

### Testes

```bash
pytest                 # testes da coleta, das notas e do build (rapidos, sem rede)
ruff check .           # lint

# teste da pagina num navegador de verdade
pip install -e ".[e2e]" && python -m playwright install chromium
pytest e2e
```

## Dados abertos

Tudo que a página mostra sai de arquivos JSON estáticos, que podem ser usados direto (CC BY 4.0):

| Arquivo | O que tem |
|---|---|
| [`dados/latest.json`](https://guilhermeoliveirabrito.github.io/farol-gov/dados/latest.json) | Resultado completo da última varredura, com o detalhe de cada item |
| [`dados/historico.json`](https://guilhermeoliveirabrito.github.io/farol-gov/dados/historico.json) | Média nacional e adoção de cada item, varredura por varredura |
| `dados/uf/<UF>.json` | Detalhes das cidades de um estado (ex.: [`PE.json`](https://guilhermeoliveirabrito.github.io/farol-gov/dados/uf/PE.json)) |
| [`podio.xml`](https://guilhermeoliveirabrito.github.io/farol-gov/podio.xml) | Feed Atom com o pódio de cada semana |
| [`data/historico/`](data/historico) | Um arquivo compacto por dia de varredura, para reconstruir a série inteira |

### Selo

Cada prefeitura tem um selo SVG que se atualiza sozinho, no endereço `selos/<código IBGE>.svg`. Para o Recife, por exemplo:

```markdown
[![farol-gov](https://guilhermeoliveirabrito.github.io/farol-gov/selos/2611606.svg)](https://guilhermeoliveirabrito.github.io/farol-gov/#m-2611606)
```

A ficha de cada cidade na página já mostra o código pronto para copiar.

## De onde vêm os domínios

A lista de municípios e seus sites oficiais vem do [Wikidata](https://www.wikidata.org/) (propriedade P856, ligada ao código IBGE). O Wikidata erra com frequência: aponta site de turismo, da câmara municipal, portal de notícias ou domínio que já não existe. Por isso a coleta faz uma conferência:

1. Aplica as correções revisadas à mão em [`data/correcoes.csv`](data/correcoes.csv).
2. Quando o site do Wikidata é suspeito (fora do `.gov.br`, da câmara, portal genérico), não existe no DNS ou nem foi cadastrado, procura o padrão oficial `<nome>.<uf>.gov.br` e variações (`www.`, `pm`, `prefeitura`). Só órgão público registra `.gov.br`, então o que existir ali é da prefeitura.

Tudo que foi trocado fica em [`data/dominios_corrigidos.csv`](data/dominios_corrigidos.csv), com o motivo. Se o site da sua cidade estiver errado, o melhor é corrigir no Wikidata, porque assim vale para todo mundo. Também dá para abrir uma issue ou mandar um PR em `data/correcoes.csv`.

## Roadmap

- [x] Checks de DNS (DNSSEC, SPF, DMARC)
- [x] Checks web (HTTPS, redirect, TLS, HSTS, headers, security.txt)
- [x] Varredura semanal via GitHub Actions
- [x] Página com ranking por estado e município (GitHub Pages)
- [x] Guia de correção para cada item ([docs/como-corrigir.md](docs/como-corrigir.md))
- [x] Detecção de cadastros suspeitos no Wikidata
- [x] Histórico semanal, gráfico de evolução e variação de posição de cada cidade
- [x] Testar se o servidor ainda aceita TLS 1.0/1.1
- [x] Conteúdo misto, cookies e CAA
- [x] Medalhas da semana e hall da fama
- [ ] Domínios estaduais e federais
- [ ] DMARC herdado do domínio organizacional

## Contribuindo

Issues e PRs são bem-vindos. Um jeito fácil de começar: o arquivo [`data/revisar_wikidata.csv`](data/revisar_wikidata.csv) lista municípios com site errado ou desatualizado no Wikidata. Corrigir lá melhora o farol e todo projeto que usa esses dados. Se você trabalha na TI de algum órgão e quer contestar um resultado, abra uma issue que a gente olha junto.

## Licença

Código sob [MIT](LICENSE). Os dados gerados em `data/` são publicados sob [CC BY 4.0](data/LICENSE).
