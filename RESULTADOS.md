# Resultados

Varredura de 2026-11-13. 3633 domínios verificados, 3239 acessíveis (394 não responderam e ficaram fora da nota).

89 municípios acessíveis ficaram fora do ranking porque o domínio cadastrado precisa de revisão (fora do `.gov.br` ou repetido em mais de um município). Lista em [data/revisar_wikidata.csv](data/revisar_wikidata.csv).

Metodologia: [docs/metodologia.md](docs/metodologia.md). Dados completos: [data/resultados/latest.json](data/resultados/latest.json).

## Conceitos

| Conceito | Municípios | % |
|---|---|---|
| A | 7 | 0.2% |
| B | 277 | 8.8% |
| C | 1738 | 55.2% |
| D | 1042 | 33.1% |
| F | 86 | 2.7% |

## Adoção de cada item

| Item | Atende | Parcial |
|---|---|---|
| HTTPS com certificado válido | 96.8% | 0.0% |
| HTTP redireciona para HTTPS | 63.7% | 0.0% |
| TLS 1.2 ou superior | 99.1% | 0.0% |
| HSTS (1 ano ou mais) | 27.8% | 2.3% |
| Headers de segurança | 29.7% | 19.9% |
| security.txt | 0.4% | 0.0% |
| DNSSEC | 1.0% | 0.0% |
| SPF | 89.0% | 7.0% |
| DMARC bloqueando e-mail falso | 30.0% | 37.2% |

## Ranking por estado

| # | UF | Nota média | Municípios avaliados |
|---|---|---|---|
| 1 | SE | 82.9 | 19 |
| 2 | AC | 75.3 | 18 |
| 3 | CE | 66.0 | 77 |
| 4 | RR | 64.6 | 12 |
| 5 | RN | 62.5 | 44 |
| 6 | PR | 60.9 | 147 |
| 7 | RO | 60.2 | 12 |
| 8 | AM | 60.0 | 16 |
| 9 | ES | 59.9 | 56 |
| 10 | PA | 59.4 | 40 |
| 11 | AP | 58.8 | 5 |
| 12 | SP | 58.7 | 629 |
| 13 | MA | 58.7 | 55 |
| 14 | RJ | 58.7 | 84 |
| 15 | PE | 57.6 | 179 |
| 16 | GO | 57.4 | 78 |
| 17 | TO | 57.3 | 18 |
| 18 | AL | 57.2 | 38 |
| 19 | BA | 57.0 | 182 |
| 20 | PB | 56.7 | 46 |
| 21 | MG | 56.5 | 695 |
| 22 | MS | 56.5 | 67 |
| 23 | RS | 55.9 | 389 |
| 24 | SC | 54.6 | 70 |
| 25 | MT | 53.8 | 141 |
| 26 | PI | 51.1 | 33 |

## Top 20 municípios

| Município | UF | Domínio | Nota |
|---|---|---|---|
| Amparo do São Francisco | SE | `amparodosaofrancisco.se.gov.br` | 93.8 (A) |
| Barra dos Coqueiros | SE | `www.barradoscoqueiros.se.gov.br` | 93.8 (A) |
| Lagarto | SE | `www.lagarto.se.gov.br` | 93.8 (A) |
| Simão Dias | SE | `www.simaodias.se.gov.br` | 93.8 (A) |
| São Cristóvão | SE | `www.saocristovao.se.gov.br` | 93.8 (A) |
| Anápolis | GO | `www.anapolis.go.gov.br` | 90.6 (A) |
| Brusque | SC | `www.brusque.sc.gov.br` | 90.6 (A) |
| Aracaju | SE | `www.aracaju.se.gov.br` | 87.5 (B) |
| Canindé de São Francisco | SE | `www.caninde.se.gov.br` | 87.5 (B) |
| Lagoa dos Gatos | PE | `www.lagoadosgatos.pe.gov.br` | 87.5 (B) |
| Rio Formoso | PE | `www.rioformoso.pe.gov.br` | 87.5 (B) |
| Salgadinho | PE | `www.salgadinho.pe.gov.br` | 87.5 (B) |
| Taquaritinga do Norte | PE | `www.taquaritingadonorte.pe.gov.br` | 87.5 (B) |
| Itanhaém | SP | `www.itanhaem.sp.gov.br` | 84.4 (B) |
| Agudo | RS | `www.agudo.rs.gov.br` | 81.2 (B) |
| Arroio do Sal | RS | `www.arroiodosal.rs.gov.br` | 81.2 (B) |
| Camocim | CE | `www.camocim.ce.gov.br` | 81.2 (B) |
| Campos dos Goytacazes | RJ | `www.campos.rj.gov.br` | 81.2 (B) |
| Carneiros | AL | `www.carneiros.al.gov.br` | 81.2 (B) |
| Conceição do Pará | MG | `www.conceicaodopara.mg.gov.br` | 81.2 (B) |

## Qualidade da coleta

| Item | Erros | Motivo mais comum |
|---|---|---|
| https | 397 | timeout |
| redirect | 378 | timeout |
| tls | 397 | timeout |
| hsts | 88 | dominio nao resolve |
| headers | 413 | timeout |
| security_txt | 103 | dominio nao resolve |
| dnssec | 109 | dominio nao resolve |
| spf | 19 | NoNameservers |
| dmarc | 20 | NoNameservers |
