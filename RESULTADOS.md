# Resultados

Varredura de 2026-11-16. 3633 domínios verificados, 3228 acessíveis (405 não responderam e ficaram fora da nota).

88 municípios acessíveis ficaram fora do ranking porque o domínio cadastrado precisa de revisão (fora do `.gov.br` ou repetido em mais de um município). Lista em [data/revisar_wikidata.csv](data/revisar_wikidata.csv).

Metodologia: [docs/metodologia.md](docs/metodologia.md). Dados completos: [data/resultados/latest.json](data/resultados/latest.json).

## Conceitos

| Conceito | Municípios | % |
|---|---|---|
| A | 6 | 0.2% |
| B | 158 | 5.0% |
| C | 1305 | 41.6% |
| D | 1456 | 46.4% |
| F | 215 | 6.8% |

## Adoção de cada item

| Item | Atende | Parcial |
|---|---|---|
| HTTPS com certificado válido | 96.5% | 0.0% |
| HTTP redireciona para HTTPS | 63.8% | 0.0% |
| TLS 1.2 ou superior | 99.1% | 0.0% |
| HSTS (1 ano ou mais) | 27.7% | 2.4% |
| Headers de segurança | 30.1% | 19.9% |
| security.txt | 0.4% | 0.0% |
| DNSSEC | 1.0% | 0.0% |
| SPF | 66.8% | 5.5% |
| DMARC bloqueando e-mail falso | 21.9% | 27.7% |

## Ranking por estado

| # | UF | Nota média | Municípios avaliados |
|---|---|---|---|
| 1 | SE | 82.9 | 19 |
| 2 | AC | 75.3 | 18 |
| 3 | CE | 66.0 | 77 |
| 4 | RR | 64.6 | 12 |
| 5 | RN | 62.5 | 44 |
| 6 | RO | 60.2 | 12 |
| 7 | AM | 60.0 | 16 |
| 8 | MA | 59.0 | 55 |
| 9 | AP | 58.8 | 5 |
| 10 | PA | 58.6 | 40 |
| 11 | TO | 57.9 | 19 |
| 12 | PE | 57.6 | 179 |
| 13 | GO | 57.4 | 78 |
| 14 | AL | 57.2 | 38 |
| 15 | PB | 56.7 | 46 |
| 16 | BA | 56.7 | 182 |
| 17 | RS | 56.1 | 383 |
| 18 | MS | 56.0 | 67 |
| 19 | SC | 55.9 | 67 |
| 20 | MT | 54.6 | 141 |
| 21 | MG | 52.9 | 693 |
| 22 | PR | 51.0 | 147 |
| 23 | PI | 50.8 | 33 |
| 24 | ES | 49.6 | 55 |
| 25 | RJ | 49.3 | 83 |
| 26 | SP | 47.7 | 631 |

## Top 20 municípios

| Município | UF | Domínio | Nota |
|---|---|---|---|
| Amparo do São Francisco | SE | `amparodosaofrancisco.se.gov.br` | 93.8 (A) |
| Barra dos Coqueiros | SE | `www.barradoscoqueiros.se.gov.br` | 93.8 (A) |
| Lagarto | SE | `www.lagarto.se.gov.br` | 93.8 (A) |
| Simão Dias | SE | `www.simaodias.se.gov.br` | 93.8 (A) |
| São Cristóvão | SE | `www.saocristovao.se.gov.br` | 93.8 (A) |
| Anápolis | GO | `www.anapolis.go.gov.br` | 90.6 (A) |
| Aracaju | SE | `www.aracaju.se.gov.br` | 87.5 (B) |
| Canindé de São Francisco | SE | `www.caninde.se.gov.br` | 87.5 (B) |
| Lagoa dos Gatos | PE | `www.lagoadosgatos.pe.gov.br` | 87.5 (B) |
| Rio Formoso | PE | `www.rioformoso.pe.gov.br` | 87.5 (B) |
| Salgadinho | PE | `www.salgadinho.pe.gov.br` | 87.5 (B) |
| Taquaritinga do Norte | PE | `www.taquaritingadonorte.pe.gov.br` | 87.5 (B) |
| Agudo | RS | `www.agudo.rs.gov.br` | 81.2 (B) |
| Arroio do Sal | RS | `www.arroiodosal.rs.gov.br` | 81.2 (B) |
| Camocim | CE | `www.camocim.ce.gov.br` | 81.2 (B) |
| Carneiros | AL | `www.carneiros.al.gov.br` | 81.2 (B) |
| Conceição do Pará | MG | `www.conceicaodopara.mg.gov.br` | 81.2 (B) |
| Dormentes | PE | `dormentes.pe.gov.br` | 81.2 (B) |
| Equador | RN | `www.equador.rn.gov.br` | 81.2 (B) |
| Estância | SE | `www.estancia.se.gov.br` | 81.2 (B) |

## Qualidade da coleta

| Item | Erros | Motivo mais comum |
|---|---|---|
| https | 391 | timeout |
| redirect | 376 | timeout |
| tls | 391 | timeout |
| hsts | 78 | dominio nao resolve |
| headers | 424 | timeout |
| security_txt | 98 | dominio nao resolve |
| dnssec | 875 | LifetimeTimeout |
| spf | 823 | LifetimeTimeout |
| dmarc | 810 | LifetimeTimeout |
