# Resultados

Varredura de 2026-11-20. 5444 domínios verificados, 5046 acessíveis (398 não responderam e ficaram fora da nota).

31 municípios acessíveis ficaram fora do ranking porque o domínio cadastrado precisa de revisão (fora do `.gov.br` ou repetido em mais de um município). Lista em [data/revisar_wikidata.csv](data/revisar_wikidata.csv).

Metodologia: [docs/metodologia.md](docs/metodologia.md). Dados completos: [data/resultados/latest.json](data/resultados/latest.json).

## Conceitos

| Conceito | Municípios | % |
|---|---|---|
| A | 0 | 0.0% |
| B | 52 | 1.0% |
| C | 2180 | 43.5% |
| D | 2636 | 52.6% |
| F | 147 | 2.9% |

## Adoção de cada item

| Item | Atende | Parcial |
|---|---|---|
| HTTPS com certificado válido | 96.3% | 0.7% |
| HTTP redireciona para HTTPS | 66.8% | 0.0% |
| TLS 1.2 ou superior | 99.4% | 0.0% |
| Recusa TLS 1.0 e 1.1 | 68.3% | 0.0% |
| HSTS (1 ano ou mais) | 27.3% | 2.2% |
| Headers de segurança | 31.4% | 19.2% |
| Sem conteúdo misto | 92.0% | 3.6% |
| Cookies com Secure e HttpOnly | 66.7% | 4.7% |
| security.txt | 0.4% | 0.0% |
| Não mostra a versão do software | 65.1% | 0.0% |
| DNSSEC | 1.9% | 0.0% |
| CAA (quem pode emitir certificado) | 25.4% | 0.0% |
| SPF | 87.8% | 8.0% |
| DMARC bloqueando e-mail falso | 29.0% | 36.8% |
| E-mail com TLS obrigatório (MTA-STS) | 0.3% | 0.2% |

## Ranking por estado

| # | UF | Nota média | Municípios avaliados |
|---|---|---|---|
| 1 | SE | 74.6 | 73 |
| 2 | AC | 63.5 | 22 |
| 3 | CE | 61.4 | 181 |
| 4 | PA | 60.1 | 126 |
| 5 | AP | 59.5 | 14 |
| 6 | RR | 59.0 | 13 |
| 7 | PR | 57.4 | 298 |
| 8 | GO | 56.4 | 232 |
| 9 | RO | 55.4 | 42 |
| 10 | RN | 54.6 | 165 |
| 11 | ES | 54.5 | 69 |
| 12 | MA | 54.2 | 200 |
| 13 | AM | 54.0 | 55 |
| 14 | BA | 53.7 | 410 |
| 15 | RJ | 53.3 | 89 |
| 16 | MT | 53.1 | 141 |
| 17 | TO | 52.6 | 122 |
| 18 | AL | 52.4 | 100 |
| 19 | MS | 52.3 | 76 |
| 20 | PE | 52.0 | 181 |
| 21 | RS | 51.7 | 435 |
| 22 | MG | 51.6 | 842 |
| 23 | SP | 51.5 | 630 |
| 24 | PI | 49.9 | 181 |
| 25 | SC | 49.6 | 101 |
| 26 | PB | 48.1 | 217 |

## Top 20 municípios

| Município | UF | Domínio | Nota |
|---|---|---|---|
| Amparo do São Francisco | SE | `amparodosaofrancisco.se.gov.br` | 84.5 (B) |
| Aquidabã | SE | `www.aquidaba.se.gov.br` | 84.5 (B) |
| Barra dos Coqueiros | SE | `www.barradoscoqueiros.se.gov.br` | 84.5 (B) |
| Campo do Brito | SE | `www.campodobrito.se.gov.br` | 84.5 (B) |
| Canhoba | SE | `www.canhoba.se.gov.br` | 84.5 (B) |
| Frei Paulo | SE | `www.freipaulo.se.gov.br` | 84.5 (B) |
| Itabaianinha | SE | `www.itabaianinha.se.gov.br` | 84.5 (B) |
| Lagarto | SE | `www.lagarto.se.gov.br` | 84.5 (B) |
| Macambira | SE | `www.macambira.se.gov.br` | 84.5 (B) |
| Maruim | SE | `www.maruim.se.gov.br` | 84.5 (B) |
| Muribeca | SE | `www.muribeca.se.gov.br` | 84.5 (B) |
| Neópolis | SE | `www.neopolis.se.gov.br` | 84.5 (B) |
| Nossa Senhora das Dores | SE | `www.nossasenhoradasdores.se.gov.br` | 84.5 (B) |
| Pacatuba | SE | `www.pacatuba.se.gov.br` | 84.5 (B) |
| Pedrinhas | SE | `www.pedrinhas.se.gov.br` | 84.5 (B) |
| Poço Verde | SE | `www.pocoverde.se.gov.br` | 84.5 (B) |
| Propriá | SE | `www.propria.se.gov.br` | 84.5 (B) |
| Rosário do Catete | SE | `www.rosariodocatete.se.gov.br` | 84.5 (B) |
| Simão Dias | SE | `www.simaodias.se.gov.br` | 84.5 (B) |
| Siriri | SE | `www.siriri.se.gov.br` | 84.5 (B) |

## Qualidade da coleta

| Item | Erros | Motivo mais comum |
|---|---|---|
| https | 416 | timeout |
| redirect | 391 | timeout |
| tls | 416 | timeout |
| tls_antigo | 417 | timeout |
| hsts | 15 | dominio nao resolve |
| headers | 418 | timeout |
| conteudo_misto | 453 | timeout |
| cookies | 418 | timeout |
| security_txt | 30 | dominio nao resolve |
| versao_exposta | 418 | timeout |
| dnssec | 23 | dominio nao resolve |
| caa | 8 | NoNameservers |
| spf | 8 | NoNameservers |
| dmarc | 8 | NoNameservers |
| email_tls | 8 | NoNameservers |

Comparação com a varredura de 2026-11-19: 4855 cidades mudaram de posição.

## Quem mais subiu

| Município | UF | Posição | Variação |
|---|---|---|---|
| Mata Grande | AL | 4774º → 611º | ↑ 4163 |
| Aimorés | MG | 3969º → 239º | ↑ 3730 |
| Araras | SP | 4852º → 1406º | ↑ 3446 |
| Belo Oriente | MG | 4651º → 1395º | ↑ 3256 |
| Biquinhas | MG | 4651º → 1395º | ↑ 3256 |
| Aquidauana | MS | 4849º → 2384º | ↑ 2465 |
| Castanhal | PA | 4874º → 2720º | ↑ 2154 |
| Timon | MA | 1940º → 85º | ↑ 1855 |
| Manicoré | AM | 2911º → 1060º | ↑ 1851 |
| Rio Preto da Eva | AM | 2911º → 1060º | ↑ 1851 |

## Quem mais caiu

| Município | UF | Posição | Variação |
|---|---|---|---|
| Sabará | MG | 1420º → 4186º | ↓ 2766 |
| Moreno | PE | 1976º → 4498º | ↓ 2522 |
| Mesquita | RJ | 2161º → 4306º | ↓ 2145 |
| Capão Bonito | SP | 2161º → 4306º | ↓ 2145 |
| Abreu e Lima | PE | 1952º → 3993º | ↓ 2041 |
| Santa Cecília | PB | 1976º → 3783º | ↓ 1807 |
| Santa Cruz | PE | 1976º → 3783º | ↓ 1807 |
| Guaporema | PR | 1962º → 3754º | ↓ 1792 |
| Varzelândia | MG | 2161º → 3909º | ↓ 1748 |
| Boa Vista do Ramos | AM | 2828º → 4564º | ↓ 1736 |
