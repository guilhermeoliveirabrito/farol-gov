# Resultados

Varredura de 2026-11-20. 5442 domínios verificados, 5044 acessíveis (398 não responderam e ficaram fora da nota).

25 municípios acessíveis ficaram fora do ranking porque o domínio cadastrado precisa de revisão (fora do `.gov.br` ou repetido em mais de um município). Lista em [data/revisar_wikidata.csv](data/revisar_wikidata.csv).

Metodologia: [docs/metodologia.md](docs/metodologia.md). Dados completos: [data/resultados/latest.json](data/resultados/latest.json).

## Conceitos

| Conceito | Municípios | % |
|---|---|---|
| A | 29 | 0.6% |
| B | 389 | 7.8% |
| C | 3202 | 63.8% |
| D | 1303 | 26.0% |
| F | 96 | 1.9% |

## Adoção de cada item

| Item | Atende | Parcial |
|---|---|---|
| HTTPS com certificado válido | 96.2% | 0.7% |
| HTTP redireciona para HTTPS | 66.8% | 0.0% |
| TLS 1.2 ou superior | 99.4% | 0.0% |
| Recusa TLS 1.0 e 1.1 | 68.2% | 0.0% |
| HSTS (1 ano ou mais) | 27.3% | 2.2% |
| Headers de segurança | 31.4% | 19.1% |
| Sem conteúdo misto | 91.8% | 3.8% |
| Cookies com Secure e HttpOnly | 66.7% | 4.7% |
| security.txt | 0.4% | 0.0% |
| Não mostra a versão do software | 64.9% | 0.0% |
| DNSSEC | 1.9% | 0.0% |
| CAA (quem pode emitir certificado) | 25.3% | 0.0% |
| SPF | 87.7% | 7.9% |
| DMARC bloqueando e-mail falso | 28.9% | 36.8% |
| E-mail com TLS obrigatório (MTA-STS) | 0.3% | 0.3% |
| Privacidade (LGPD) na página inicial | 28.9% | 58.5% |

## Ranking por estado

| # | UF | Nota média | Municípios avaliados |
|---|---|---|---|
| 1 | SE | 79.2 | 73 |
| 2 | AC | 70.3 | 22 |
| 3 | CE | 67.6 | 180 |
| 4 | PA | 67.2 | 126 |
| 5 | RR | 66.0 | 13 |
| 6 | GO | 65.2 | 232 |
| 7 | AP | 64.8 | 14 |
| 8 | PR | 64.0 | 298 |
| 9 | RO | 63.0 | 42 |
| 10 | BA | 61.1 | 407 |
| 11 | AM | 60.4 | 55 |
| 12 | RN | 60.3 | 165 |
| 13 | ES | 60.0 | 69 |
| 14 | MA | 59.6 | 200 |
| 15 | RJ | 59.3 | 87 |
| 16 | PE | 59.0 | 181 |
| 17 | TO | 57.8 | 122 |
| 18 | MS | 57.7 | 76 |
| 19 | SP | 57.5 | 631 |
| 20 | AL | 57.4 | 100 |
| 21 | RS | 56.7 | 436 |
| 22 | MT | 56.7 | 141 |
| 23 | MG | 56.5 | 844 |
| 24 | SC | 55.5 | 99 |
| 25 | PI | 54.5 | 189 |
| 26 | PB | 53.1 | 217 |

## Top 20 municípios

| Município | UF | Domínio | Nota |
|---|---|---|---|
| Amparo do São Francisco | SE | `amparodosaofrancisco.se.gov.br` | 90.0 (A) |
| Aquidabã | SE | `www.aquidaba.se.gov.br` | 90.0 (A) |
| Barra dos Coqueiros | SE | `www.barradoscoqueiros.se.gov.br` | 90.0 (A) |
| Campo do Brito | SE | `www.campodobrito.se.gov.br` | 90.0 (A) |
| Canhoba | SE | `www.canhoba.se.gov.br` | 90.0 (A) |
| Capela | SE | `www.capela.se.gov.br` | 90.0 (A) |
| Divina Pastora | SE | `www.divinapastora.se.gov.br` | 90.0 (A) |
| Flexeiras | AL | `www.flexeiras.al.gov.br` | 90.0 (A) |
| Frei Paulo | SE | `www.freipaulo.se.gov.br` | 90.0 (A) |
| Itabaianinha | SE | `www.itabaianinha.se.gov.br` | 90.0 (A) |
| Lagarto | SE | `www.lagarto.se.gov.br` | 90.0 (A) |
| Macambira | SE | `www.macambira.se.gov.br` | 90.0 (A) |
| Maruim | SE | `www.maruim.se.gov.br` | 90.0 (A) |
| Muribeca | SE | `www.muribeca.se.gov.br` | 90.0 (A) |
| Nossa Senhora das Dores | SE | `www.nossasenhoradasdores.se.gov.br` | 90.0 (A) |
| Pacatuba | SE | `www.pacatuba.se.gov.br` | 90.0 (A) |
| Pedrinhas | SE | `www.pedrinhas.se.gov.br` | 90.0 (A) |
| Poço Verde | SE | `www.pocoverde.se.gov.br` | 90.0 (A) |
| Propriá | SE | `www.propria.se.gov.br` | 90.0 (A) |
| Rio Formoso | PE | `www.rioformoso.pe.gov.br` | 90.0 (A) |

## Qualidade da coleta

| Item | Erros | Motivo mais comum |
|---|---|---|
| https | 408 | timeout |
| redirect | 390 | timeout |
| tls | 408 | timeout |
| tls_antigo | 408 | timeout |
| hsts | 15 | dominio nao resolve |
| headers | 413 | timeout |
| conteudo_misto | 445 | timeout |
| cookies | 413 | timeout |
| security_txt | 31 | dominio nao resolve |
| versao_exposta | 413 | timeout |
| dnssec | 46 | LifetimeTimeout |
| caa | 10 | NoNameservers |
| spf | 10 | NoNameservers |
| dmarc | 10 | NoNameservers |
| email_tls | 10 | NoNameservers |
| privacidade | 454 | timeout |

Comparação com a varredura de 2026-11-19: 4853 cidades mudaram de posição.

## Quem mais subiu

| Município | UF | Posição | Variação |
|---|---|---|---|
| Mata Grande | AL | 4780º → 577º | ↑ 4203 |
| Aimorés | MG | 3646º → 297º | ↑ 3349 |
| Araras | SP | 4850º → 1844º | ↑ 3006 |
| Belo Oriente | MG | 4670º → 1789º | ↑ 2881 |
| Biquinhas | MG | 4670º → 1846º | ↑ 2824 |
| Castanhal | PA | 4871º → 2317º | ↑ 2554 |
| Timon | MA | 2279º → 78º | ↑ 2201 |
| Aquidauana | MS | 4850º → 2792º | ↑ 2058 |
| Conceição do Araguaia | PA | 3029º → 1116º | ↑ 1913 |
| Vitória do Jari | AP | 3029º → 1116º | ↑ 1913 |

## Quem mais caiu

| Município | UF | Posição | Variação |
|---|---|---|---|
| Sabará | MG | 1377º → 3697º | ↓ 2320 |
| Mesquita | RJ | 1811º → 3912º | ↓ 2101 |
| Moreno | PE | 2405º → 4282º | ↓ 1877 |
| Boa Vista do Ramos | AM | 3029º → 4725º | ↓ 1696 |
| Varzelândia | MG | 1811º → 3463º | ↓ 1652 |
| Estrela de Alagoas | AL | 2783º → 4382º | ↓ 1599 |
| Rio Branco do Ivaí | PR | 2783º → 4352º | ↓ 1569 |
| Sete Lagoas | MG | 1251º → 2599º | ↓ 1348 |
| São José da Lapa | MG | 1677º → 3011º | ↓ 1334 |
| Porto Alegre | RS | 1251º → 2559º | ↓ 1308 |
