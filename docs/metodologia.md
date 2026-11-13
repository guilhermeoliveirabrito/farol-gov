# Metodologia

## Resultado de cada check

Cada verificação devolve um de quatro estados:

| Estado | Valor na nota | Significado |
|---|---|---|
| `pass` | 1.0 | Atende ao critério |
| `warn` | 0.5 | Atende parcialmente (ex.: DMARC com `p=none`) |
| `fail` | 0.0 | Não atende |
| `error` | 0.0 | Não foi possível verificar (timeout, erro de DNS etc.) |

`error` conta como zero porque, do ponto de vista do cidadão, um site que não responde direito também é um problema. Mesmo assim ele aparece separado nos dados para não ser confundido com uma falha de configuração.

Domínios que não resolvem no DNS ou não respondem nem em HTTP nem em HTTPS ficam fora do ranking e aparecem como "inacessíveis".

## Qualidade do cadastro

O site de cada município vem do Wikidata, e nem sempre o cadastro está certo. Antes de avaliar, o farol faz algumas checagens:

| Aviso | O que acontece |
|---|---|
| `dominio_alternativo` | O domínio cadastrado não existe, mas a versão com/sem `www.` existe. Avaliamos a que funciona. |
| `nao_resolve` | Nenhuma das duas versões existe no DNS. Fica sem nota. |
| `fora_do_gov_br` | O domínio não termina em `.gov.br`. É avaliado, mas fica **fora do ranking** até alguém confirmar que é mesmo o site da prefeitura (já apareceu site de associação de municípios cadastrado como site de prefeitura). |
| `dominio_compartilhado` | O mesmo domínio aparece para mais de um município. Também fica fora do ranking. |

Todos os casos vão para `data/revisar_wikidata.csv`, que serve de lista de tarefas para quem quiser corrigir o Wikidata.

## Pesos

| Check | Peso | Critério para `pass` | Quando é `warn` |
|---|---|---|---|
| `https` | 3 | Conexão HTTPS com certificado válido para o domínio | - |
| `redirect` | 2 | `http://dominio/` redireciona (até 5 saltos) para `https://` | - |
| `tls` | 2 | Versão negociada é TLS 1.2 ou 1.3 | - |
| `hsts` | 1 | `max-age` >= 31536000 (1 ano) | HSTS presente mas com `max-age` menor |
| `headers` | 1 | `X-Content-Type-Options: nosniff` **e** (`X-Frame-Options` ou CSP com `frame-ancestors`) | Só um dos dois |
| `security_txt` | 1 | `/.well-known/security.txt` responde 200 e tem campo `Contact:` | - |
| `dnssec` | 2 | Resolver validador marca a resposta com o bit AD | - |
| `spf` | 1 | Registro `v=spf1` terminando em `-all` ou `~all` | `?all` ou sem mecanismo `all` |
| `dmarc` | 3 | `_dmarc` com `p=reject` ou `p=quarantine` | `p=none` |

Total: 16 pontos.

DMARC e HTTPS têm peso maior porque são os que mais afetam o cidadão diretamente: um protege contra golpe por e-mail em nome do órgão, o outro protege o que é digitado no site.

## Nota

```
nota = 100 * soma(peso * valor) / soma(pesos)
```

| Conceito | Nota |
|---|---|
| A | >= 90 |
| B | >= 75 |
| C | >= 55 |
| D | >= 35 |
| F | < 35 |

## Detalhes técnicos

- **DNS**: consultas feitas em resolvers públicos que validam DNSSEC (Cloudflare `1.1.1.1` e Google `8.8.8.8`). O DNSSEC é considerado válido quando a resposta para o registro `A` vem com a flag AD.
- **Domínio de e-mail**: SPF e DMARC são consultados no domínio do site sem o `www.` (ex.: `www.recife.pe.gov.br` vira `recife.pe.gov.br`).
- **TLS**: registramos a versão negociada pelo cliente padrão do Python. Ainda não testamos se o servidor *aceita* versões antigas; isso está no roadmap.
- **Timeouts**: 10 segundos por conexão, com uma nova tentativa em caso de erro de rede.

## Limitações conhecidas

- A lista de domínios depende do Wikidata. Município sem site cadastrado lá não entra.
- Alguns servidores bloqueiam IPs de datacenter (como os do GitHub Actions), o que pode gerar `error` em vez do resultado real.
- O DMARC é lido só no próprio domínio. Ainda não consideramos a política herdada do domínio organizacional ([RFC 7489, seção 6.6.3](https://www.rfc-editor.org/rfc/rfc7489#section-6.6.3)).
- Um site pode ter nota boa e ainda assim ter vulnerabilidades. O farol mede higiene de configuração, não faz pentest.
