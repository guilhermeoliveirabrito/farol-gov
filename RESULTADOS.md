# Resultados

Varredura de 2026-11-20. 5442 domínios verificados, 5057 acessíveis (385 não responderam e ficaram fora da nota).

56 municípios acessíveis ficaram fora do ranking porque o domínio cadastrado precisa de revisão (fora do `.gov.br` ou repetido em mais de um município). Lista em [data/revisar_wikidata.csv](data/revisar_wikidata.csv).

Metodologia: [docs/metodologia.md](docs/metodologia.md). Dados completos: [data/resultados/latest.json](data/resultados/latest.json).

## Conceitos

| Conceito | Municípios | % |
|---|---|---|
| A | 30 | 0.6% |
| B | 389 | 7.8% |
| C | 3197 | 63.9% |
| D | 1290 | 25.8% |
| F | 95 | 1.9% |

## Adoção de cada item

| Item | Atende | Parcial |
|---|---|---|
| HTTPS com certificado válido | 96.3% | 0.7% |
| HTTP redireciona para HTTPS | 66.7% | 0.0% |
| TLS 1.2 ou superior | 99.4% | 0.0% |
| Recusa TLS 1.0 e 1.1 | 68.2% | 0.0% |
| HSTS (1 ano ou mais) | 27.4% | 2.2% |
| Headers de segurança | 31.5% | 19.2% |
| Sem conteúdo misto | 92.1% | 3.6% |
| Cookies com Secure e HttpOnly | 66.8% | 4.7% |
| security.txt | 0.4% | 0.0% |
| Não mostra a versão do software | 65.2% | 0.0% |
| DNSSEC | 1.9% | 0.0% |
| CAA (quem pode emitir certificado) | 25.4% | 0.0% |
| SPF | 87.7% | 8.0% |
| DMARC bloqueando e-mail falso | 29.0% | 36.9% |
| E-mail com TLS obrigatório (MTA-STS) | 0.3% | 0.3% |

## Ranking por estado

| # | UF | Nota média | Municípios avaliados |
|---|---|---|---|
| 1 | SE | 79.3 | 73 |
| 2 | AC | 70.3 | 22 |
| 3 | CE | 67.7 | 179 |
| 4 | PA | 67.2 | 126 |
| 5 | RR | 66.0 | 13 |
| 6 | GO | 65.2 | 232 |
| 7 | AP | 64.3 | 14 |
| 8 | PR | 64.0 | 298 |
| 9 | RO | 63.0 | 42 |
| 10 | BA | 61.0 | 407 |
| 11 | RN | 60.8 | 163 |
| 12 | AM | 60.4 | 55 |
| 13 | ES | 60.0 | 69 |
| 14 | MA | 59.6 | 200 |
| 15 | RJ | 59.6 | 88 |
| 16 | PE | 59.0 | 181 |
| 17 | TO | 57.8 | 122 |
| 18 | MS | 57.7 | 76 |
| 19 | SP | 57.5 | 631 |
| 20 | AL | 57.4 | 100 |
| 21 | MT | 56.9 | 141 |
| 22 | RS | 56.7 | 430 |
| 23 | MG | 56.6 | 844 |
| 24 | SC | 55.6 | 99 |
| 25 | PI | 55.0 | 180 |
| 26 | PB | 53.1 | 216 |

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
| Neópolis | SE | `www.neopolis.se.gov.br` | 90.0 (A) |
| Nossa Senhora das Dores | SE | `www.nossasenhoradasdores.se.gov.br` | 90.0 (A) |
| Pacatuba | SE | `www.pacatuba.se.gov.br` | 90.0 (A) |
| Pedrinhas | SE | `www.pedrinhas.se.gov.br` | 90.0 (A) |
| Poço Verde | SE | `www.pocoverde.se.gov.br` | 90.0 (A) |
| Propriá | SE | `www.propria.se.gov.br` | 90.0 (A) |

## Qualidade da coleta

| Item | Erros | Motivo mais comum |
|---|---|---|
| https | 425 | timeout |
| redirect | 378 | timeout |
| tls | 425 | timeout |
| tls_antigo | 425 | timeout |
| hsts | 15 | dominio nao resolve |
| headers | 428 | timeout |
| conteudo_misto | 461 | timeout |
| cookies | 428 | timeout |
| security_txt | 30 | dominio nao resolve |
| versao_exposta | 428 | timeout |
| dnssec | 24 | dominio nao resolve |
| caa | 9 | NoNameservers |
| spf | 10 | NoNameservers |
| dmarc | 10 | NoNameservers |
| email_tls | 10 | NoNameservers |

Comparação com a varredura de 2026-11-19: 4841 cidades mudaram de posição.

## Quem mais subiu

| Município | UF | Posição | Variação |
|---|---|---|---|
| Mata Grande | AL | 4780º → 581º | ↑ 4199 |
| Aimorés | MG | 3646º → 272º | ↑ 3374 |
| Araras | SP | 4850º → 1827º | ↑ 3023 |
| Belo Oriente | MG | 4670º → 1840º | ↑ 2830 |
| Biquinhas | MG | 4670º → 1840º | ↑ 2830 |
| Castanhal | PA | 4871º → 2240º | ↑ 2631 |
| Timon | MA | 2279º → 72º | ↑ 2207 |
| Aquidauana | MS | 4850º → 2749º | ↑ 2101 |
| Conceição do Araguaia | PA | 3029º → 1205º | ↑ 1824 |
| Vitória do Jari | AP | 3029º → 1205º | ↑ 1824 |

## Quem mais caiu

| Município | UF | Posição | Variação |
|---|---|---|---|
| Sabará | MG | 1377º → 3629º | ↓ 2252 |
| Moreno | PE | 2405º → 4279º | ↓ 1874 |
| Boa Vista do Ramos | AM | 3029º → 4712º | ↓ 1683 |
| Varzelândia | MG | 1811º → 3484º | ↓ 1673 |
| Estrela de Alagoas | AL | 2783º → 4377º | ↓ 1594 |
| Rio Branco do Ivaí | PR | 2783º → 4335º | ↓ 1552 |
| Sete Lagoas | MG | 1251º → 2681º | ↓ 1430 |
| São José da Lapa | MG | 1677º → 2974º | ↓ 1297 |
| Ministro Andreazza | RO | 1811º → 3051º | ↓ 1240 |
| Amapá | AP | 1377º → 2604º | ↓ 1227 |
