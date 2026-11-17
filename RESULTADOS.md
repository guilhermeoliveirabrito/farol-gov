# Resultados

Varredura de 2026-11-17. 3633 domínios verificados, 3278 acessíveis (355 não responderam e ficaram fora da nota).

143 municípios acessíveis ficaram fora do ranking porque o domínio cadastrado precisa de revisão (fora do `.gov.br` ou repetido em mais de um município). Lista em [data/revisar_wikidata.csv](data/revisar_wikidata.csv).

Metodologia: [docs/metodologia.md](docs/metodologia.md). Dados completos: [data/resultados/latest.json](data/resultados/latest.json).

## Conceitos

| Conceito | Municípios | % |
|---|---|---|
| A | 9 | 0.3% |
| B | 302 | 9.6% |
| C | 2018 | 64.4% |
| D | 758 | 24.2% |
| F | 48 | 1.5% |

## Adoção de cada item

| Item | Atende | Parcial |
|---|---|---|
| HTTPS com certificado válido | 96.0% | 0.6% |
| HTTP redireciona para HTTPS | 63.6% | 0.0% |
| TLS 1.2 ou superior | 99.0% | 0.0% |
| Recusa TLS 1.0 e 1.1 | 65.7% | 0.0% |
| HSTS (1 ano ou mais) | 27.8% | 2.4% |
| Headers de segurança | 29.9% | 20.1% |
| Sem conteúdo misto | 91.9% | 4.3% |
| Cookies com Secure e HttpOnly | 66.6% | 3.9% |
| security.txt | 0.4% | 0.0% |
| DNSSEC | 0.9% | 0.0% |
| CAA (quem pode emitir certificado) | 14.5% | 0.0% |
| SPF | 77.0% | 5.8% |
| DMARC bloqueando e-mail falso | 26.0% | 32.6% |

## Ranking por estado

| # | UF | Nota média | Municípios avaliados |
|---|---|---|---|
| 1 | SE | 80.3 | 19 |
| 2 | AC | 70.8 | 18 |
| 3 | CE | 70.6 | 74 |
| 4 | RR | 67.6 | 12 |
| 5 | GO | 66.8 | 76 |
| 6 | PR | 65.4 | 145 |
| 7 | RN | 64.4 | 45 |
| 8 | MA | 64.2 | 54 |
| 9 | AP | 63.0 | 5 |
| 10 | PA | 63.0 | 40 |
| 11 | AM | 62.7 | 16 |
| 12 | ES | 62.4 | 55 |
| 13 | RO | 62.2 | 12 |
| 14 | TO | 62.1 | 19 |
| 15 | RJ | 61.7 | 81 |
| 16 | BA | 61.6 | 180 |
| 17 | AL | 61.4 | 38 |
| 18 | PE | 60.8 | 179 |
| 19 | MS | 60.3 | 66 |
| 20 | MT | 59.2 | 138 |
| 21 | PB | 59.2 | 46 |
| 22 | RS | 59.0 | 387 |
| 23 | SP | 58.9 | 627 |
| 24 | MG | 58.4 | 692 |
| 25 | PI | 54.3 | 33 |
| 26 | SC | 53.8 | 78 |

## Top 20 municípios

| Município | UF | Domínio | Nota |
|---|---|---|---|
| Salgadinho | PE | `www.salgadinho.pe.gov.br` | 100.0 (A) |
| Amparo do São Francisco | SE | `amparodosaofrancisco.se.gov.br` | 94.7 (A) |
| Lagarto | SE | `www.lagarto.se.gov.br` | 94.4 (A) |
| Goiânia | GO | `www.goiania.go.gov.br` | 94.1 (A) |
| Linhares | ES | `www.linhares.es.gov.br` | 94.1 (A) |
| Piraí | RJ | `www.pirai.rj.gov.br` | 93.3 (A) |
| Rio Verde | GO | `www.rioverde.go.gov.br` | 92.9 (A) |
| Rio Formoso | PE | `www.rioformoso.pe.gov.br` | 90.0 (A) |
| Taquaritinga do Norte | PE | `www.taquaritingadonorte.pe.gov.br` | 90.0 (A) |
| Guaramiranga | CE | `www.guaramiranga.ce.gov.br` | 89.3 (B) |
| Tapiramutá | BA | `tapiramuta.ba.gov.br` | 89.3 (B) |
| Timbaúba | PE | `www.timbauba.pe.gov.br` | 89.3 (B) |
| Barra dos Coqueiros | SE | `www.barradoscoqueiros.se.gov.br` | 88.9 (B) |
| Maués | AM | `www.maues.am.gov.br` | 88.2 (B) |
| Porto Barreiro | PR | `www.portobarreiro.pr.gov.br` | 88.2 (B) |
| Simão Dias | SE | `www.simaodias.se.gov.br` | 88.2 (B) |
| Anápolis | GO | `www.anapolis.go.gov.br` | 87.5 (B) |
| Ibimirim | PE | `www.ibimirim.pe.gov.br` | 87.5 (B) |
| Lagoa dos Gatos | PE | `www.lagoadosgatos.pe.gov.br` | 87.5 (B) |
| Nossa Senhora do Socorro | SE | `socorro.se.gov.br` | 87.5 (B) |

## Qualidade da coleta

| Item | Erros | Motivo mais comum |
|---|---|---|
| https | 373 | timeout |
| redirect | 334 | timeout |
| tls | 373 | timeout |
| tls_antigo | 373 | timeout |
| hsts | 84 | dominio nao resolve |
| headers | 381 | timeout |
| conteudo_misto | 403 | timeout |
| cookies | 381 | timeout |
| security_txt | 91 | dominio nao resolve |
| dnssec | 600 | LifetimeTimeout |
| caa | 1124 | LifetimeTimeout |
| spf | 526 | LifetimeTimeout |
| dmarc | 525 | LifetimeTimeout |

Comparação com a varredura de 2026-11-16: 2648 cidades mudaram de posição.

## Quem mais subiu

| Município | UF | Posição | Variação |
|---|---|---|---|
| Dois Vizinhos | PR | 2428º → 388º | ↑ 2040 |
| Caldas | MG | 1861º → 113º | ↑ 1748 |
| Cedro do Abaeté | MG | 1861º → 113º | ↑ 1748 |
| Vera | MT | 1861º → 113º | ↑ 1748 |
| Goiatuba | GO | 2447º → 752º | ↑ 1695 |
| Valente | BA | 2503º → 846º | ↑ 1657 |
| Montezuma | MG | 1861º → 206º | ↑ 1655 |
| Charrua | RS | 1861º → 206º | ↑ 1655 |
| Ibirama | SC | 1767º → 144º | ↑ 1623 |
| Cassilândia | MS | 1767º → 206º | ↑ 1561 |

## Quem mais caiu

| Município | UF | Posição | Variação |
|---|---|---|---|
| Ponte Nova | MG | 416º → 2439º | ↓ 2023 |
| Porciúncula | RJ | 77º → 2086º | ↓ 2009 |
| Palestina | SP | 707º → 2580º | ↓ 1873 |
| Guarani d'Oeste | SP | 1024º → 2829º | ↓ 1805 |
| Naque | MG | 399º → 2179º | ↓ 1780 |
| Santo Anastácio | SP | 707º → 2439º | ↓ 1732 |
| Valparaíso | SP | 707º → 2439º | ↓ 1732 |
| Três Marias | MG | 399º → 2123º | ↓ 1724 |
| Santa Cruz do Sul | RS | 436º → 2123º | ↓ 1687 |
| Araçatuba | SP | 900º → 2580º | ↓ 1680 |
