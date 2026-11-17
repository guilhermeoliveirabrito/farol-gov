# Resultados

Varredura de 2026-11-17. 3633 domínios verificados, 3255 acessíveis (378 não responderam e ficaram fora da nota).

92 municípios acessíveis ficaram fora do ranking porque o domínio cadastrado precisa de revisão (fora do `.gov.br` ou repetido em mais de um município). Lista em [data/revisar_wikidata.csv](data/revisar_wikidata.csv).

Metodologia: [docs/metodologia.md](docs/metodologia.md). Dados completos: [data/resultados/latest.json](data/resultados/latest.json).

## Conceitos

| Conceito | Municípios | % |
|---|---|---|
| A | 7 | 0.2% |
| B | 215 | 6.8% |
| C | 2029 | 64.1% |
| D | 867 | 27.4% |
| F | 45 | 1.4% |

## Adoção de cada item

| Item | Atende | Parcial |
|---|---|---|
| HTTPS com certificado válido | 96.3% | 0.6% |
| HTTP redireciona para HTTPS | 64.0% | 0.0% |
| TLS 1.2 ou superior | 99.4% | 0.0% |
| Recusa TLS 1.0 e 1.1 | 65.5% | 0.0% |
| HSTS (1 ano ou mais) | 27.7% | 2.4% |
| Headers de segurança | 29.8% | 19.9% |
| Sem conteúdo misto | 92.5% | 4.1% |
| Cookies com Secure e HttpOnly | 66.1% | 3.9% |
| security.txt | 0.4% | 0.0% |
| DNSSEC | 0.9% | 0.0% |
| CAA (quem pode emitir certificado) | 18.0% | 0.0% |
| SPF | 89.1% | 6.9% |
| DMARC bloqueando e-mail falso | 30.3% | 37.6% |

## Ranking por estado

| # | UF | Nota média | Municípios avaliados |
|---|---|---|---|
| 1 | SE | 78.9 | 19 |
| 2 | AC | 70.3 | 18 |
| 3 | CE | 67.3 | 77 |
| 4 | RR | 66.5 | 12 |
| 5 | GO | 65.8 | 77 |
| 6 | PR | 64.9 | 147 |
| 7 | RN | 63.2 | 45 |
| 8 | RO | 62.9 | 12 |
| 9 | AP | 62.0 | 5 |
| 10 | PA | 61.9 | 39 |
| 11 | TO | 61.3 | 19 |
| 12 | MA | 60.8 | 55 |
| 13 | AM | 60.8 | 16 |
| 14 | BA | 60.7 | 182 |
| 15 | ES | 60.0 | 55 |
| 16 | RJ | 59.6 | 84 |
| 17 | PE | 59.0 | 179 |
| 18 | AL | 57.8 | 38 |
| 19 | SP | 57.4 | 631 |
| 20 | MS | 57.4 | 67 |
| 21 | PB | 57.0 | 46 |
| 22 | RS | 56.8 | 383 |
| 23 | MT | 56.7 | 141 |
| 24 | MG | 56.6 | 694 |
| 25 | SC | 56.6 | 86 |
| 26 | PI | 51.7 | 36 |

## Top 20 municípios

| Município | UF | Domínio | Nota |
|---|---|---|---|
| Amparo do São Francisco | SE | `amparodosaofrancisco.se.gov.br` | 90.0 (A) |
| Barra dos Coqueiros | SE | `www.barradoscoqueiros.se.gov.br` | 90.0 (A) |
| Lagarto | SE | `www.lagarto.se.gov.br` | 90.0 (A) |
| Rio Formoso | PE | `www.rioformoso.pe.gov.br` | 90.0 (A) |
| Salgadinho | PE | `www.salgadinho.pe.gov.br` | 90.0 (A) |
| Simão Dias | SE | `www.simaodias.se.gov.br` | 90.0 (A) |
| Taquaritinga do Norte | PE | `www.taquaritingadonorte.pe.gov.br` | 90.0 (A) |
| Anápolis | GO | `www.anapolis.go.gov.br` | 87.5 (B) |
| Itanhaém | SP | `www.itanhaem.sp.gov.br` | 87.5 (B) |
| Lagoa dos Gatos | PE | `www.lagoadosgatos.pe.gov.br` | 87.5 (B) |
| Campos dos Goytacazes | RJ | `www.campos.rj.gov.br` | 85.0 (B) |
| Canindé de São Francisco | SE | `www.caninde.se.gov.br` | 85.0 (B) |
| Goiânia | GO | `www.goiania.go.gov.br` | 85.0 (B) |
| Iracema | RR | `www.iracema.rr.gov.br` | 85.0 (B) |
| Missal | PR | `www.missal.pr.gov.br` | 85.0 (B) |
| Palmas | PR | `www.pmp.pr.gov.br` | 85.0 (B) |
| Piraí | RJ | `www.pirai.rj.gov.br` | 85.0 (B) |
| Rio Verde | GO | `www.rioverde.go.gov.br` | 85.0 (B) |
| São Cristóvão | SE | `www.saocristovao.se.gov.br` | 85.0 (B) |
| Magé | RJ | `mage.rj.gov.br` | 82.5 (B) |

## Qualidade da coleta

| Item | Erros | Motivo mais comum |
|---|---|---|
| https | 370 | timeout |
| redirect | 360 | timeout |
| tls | 370 | timeout |
| tls_antigo | 370 | timeout |
| hsts | 88 | dominio nao resolve |
| headers | 386 | timeout |
| conteudo_misto | 408 | timeout |
| cookies | 386 | timeout |
| security_txt | 95 | dominio nao resolve |
| dnssec | 107 | dominio nao resolve |
| caa | 19 | NoNameservers |
| spf | 19 | NoNameservers |
| dmarc | 19 | NoNameservers |

Comparação com a varredura de 2026-11-16: 1966 cidades mudaram de posição.

## Quem mais subiu

| Município | UF | Posição | Variação |
|---|---|---|---|
| Ibirama | SC | 1216º → 43º | ↑ 1173 |
| Campestre da Serra | RS | 1972º → 1547º | ↑ 425 |
| Araguaína | TO | 1083º → 723º | ↑ 360 |
| Aracatu | BA | 1083º → 723º | ↑ 360 |
| Barra da Estiva | BA | 1083º → 723º | ↑ 360 |
| Juazeiro | BA | 1083º → 723º | ↑ 360 |
| Lamarão | BA | 1083º → 723º | ↑ 360 |
| São Francisco do Conde | BA | 1083º → 723º | ↑ 360 |
| Cidade Gaúcha | PR | 1083º → 723º | ↑ 360 |
| Jataí | GO | 1083º → 723º | ↑ 360 |

## Quem mais caiu

| Município | UF | Posição | Variação |
|---|---|---|---|
| Jequiá da Praia | AL | 707º → 3103º | ↓ 2396 |
| Itaqui | RS | 707º → 2697º | ↓ 1990 |
| Blumenau | SC | 279º → 2232º | ↓ 1953 |
| Campina Verde | MG | 1083º → 2904º | ↓ 1821 |
| Marabá | PA | 707º → 2499º | ↓ 1792 |
| Capivari do Sul | RS | 1310º → 2975º | ↓ 1665 |
| São Leopoldo | RS | 1216º → 2755º | ↓ 1539 |
| Sobral | CE | 707º → 2232º | ↓ 1525 |
| Bandeira do Sul | MG | 707º → 2232º | ↓ 1525 |
| Diamantina | MG | 707º → 2232º | ↓ 1525 |
