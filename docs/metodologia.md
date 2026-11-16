# Metodologia

Versão atual: **2** (desde 16/11/2026). O que mudou em relação à versão 1 está no fim da página.

## Resultado de cada check

Cada verificação devolve um de quatro estados:

| Estado | Valor na nota | Significado |
|---|---|---|
| `pass` | 1.0 | Atende ao critério |
| `warn` | 0.5 | Atende parcialmente (ex.: DMARC com `p=none`) |
| `fail` | 0.0 | Não atende |
| `error` | fica fora da conta | Não foi possível verificar (timeout, DNS que não respondeu etc.) |

Um item com `error` **não vale zero**: ele sai da conta e a nota é calculada só sobre o que deu para verificar. A prefeitura não deve perder ponto por uma falha da nossa varredura. Se menos de 70% do peso total puder ser verificado, a cidade fica sem nota naquela semana, com o aviso `verificacao_incompleta`.

Domínios que não resolvem no DNS ou não respondem nem em HTTP nem em HTTPS ficam fora do ranking e aparecem como "não respondeu".

## Qualidade do cadastro

O site de cada município vem do Wikidata, e nem sempre o cadastro está certo. Antes de avaliar, o farol faz algumas checagens:

| Aviso | O que acontece |
|---|---|
| `dominio_alternativo` | O domínio cadastrado não existe, mas a versão com/sem `www.` existe. Avaliamos a que funciona. |
| `nao_resolve` | Nenhuma das duas versões existe no DNS. Fica sem nota. |
| `fora_do_gov_br` | O domínio não termina em `.gov.br`. É avaliado, mas fica **fora do ranking** até alguém confirmar que é mesmo o site da prefeitura (já apareceu site de associação de municípios cadastrado como site de prefeitura). |
| `dominio_compartilhado` | O mesmo domínio aparece para mais de um município. Também fica fora do ranking. |
| `verificacao_incompleta` | Faltou verificar itens demais (ver acima). Sem nota nesta semana. |

Todos os casos de cadastro vão para `data/revisar_wikidata.csv`, que serve de lista de tarefas para quem quiser corrigir o Wikidata.

## Pesos

| Check | Peso | Critério para `pass` | Quando é `warn` |
|---|---|---|---|
| `https` | 3 | Conexão HTTPS com certificado válido para o domínio | Certificado válido, mas vence em menos de 14 dias |
| `redirect` | 2 | `http://dominio/` redireciona (até 5 saltos) para `https://` | - |
| `tls` | 2 | Versão negociada é TLS 1.2 ou 1.3 | - |
| `tls_antigo` | 1 | O servidor **recusa** um handshake que só oferece TLS 1.0 e 1.1 | - |
| `hsts` | 1 | `max-age` >= 31536000 (1 ano) | HSTS presente mas com `max-age` menor |
| `headers` | 1 | `X-Content-Type-Options: nosniff` **e** (`X-Frame-Options` ou CSP com `frame-ancestors`) | Só um dos dois |
| `conteudo_misto` | 1 | A página inicial (em HTTPS) não carrega nada por `http://` | Só imagens/mídia por `http://` |
| `cookies` | 1 | Todos os cookies da página inicial têm `Secure` e `HttpOnly` (ou ela não define cookies) | Todos com `Secure`, algum sem `HttpOnly` |
| `security_txt` | 1 | `/.well-known/security.txt` responde 200 e tem campo `Contact:` | - |
| `dnssec` | 2 | Resolver validador marca a resposta com o bit AD | - |
| `caa` | 1 | Existe registro CAA `issue`/`issuewild` no domínio ou em um domínio acima (ex.: `sp.gov.br`) | - |
| `spf` | 1 | Registro `v=spf1` terminando em `-all` ou `~all` | `?all` ou sem mecanismo `all` |
| `dmarc` | 3 | `_dmarc` com `p=reject` ou `p=quarantine` | `p=none` |

Total: 20 pontos.

DMARC e HTTPS têm peso maior porque são os que mais afetam o cidadão diretamente: um protege contra golpe por e-mail em nome do órgão, o outro protege o que é digitado no site.

`conteudo_misto` considera falha grave (`fail`) scripts, iframes, folhas de estilo e formulários carregados por `http://`, porque eles permitem alterar a página. Links comuns (`<a href="http://...">`) não contam.

## Nota

```
nota = 100 * soma(peso * valor) / soma(pesos dos itens verificados)
```

| Conceito | Nota |
|---|---|
| A | >= 90 |
| B | >= 75 |
| C | >= 55 |
| D | >= 35 |
| F | < 35 |

## Posição e histórico

- **Posição no Brasil**: ordem das notas entre as cidades que estão no ranking. Empates dividem a mesma posição (1º, 2º, 2º, 4º...).
- **Variação**: diferença de posição em relação à varredura anterior. Como as notas têm poucos valores possíveis, muitas cidades empatam, e uma mudança pequena de nota pode mover uma cidade centenas de posições.
- **Histórico**: cada varredura completa é guardada em `data/historico/AAAA-MM-DD.json`, só com o status de cada item. **As notas das semanas antigas são recalculadas com as regras atuais**, para que a comparação faça sentido. Um item novo só entra na conta a partir da semana em que começou a ser verificado. No gráfico da página, a semana em que a metodologia mudou aparece marcada.

## Detalhes técnicos

- **DNS**: consultas em cinco resolvers públicos que validam DNSSEC (Cloudflare, Google e Quad9), com rodízio entre eles, 3 segundos por servidor, até 12 segundos por consulta e uma nova tentativa quando dá timeout. O DNSSEC é considerado válido quando a resposta para o registro `A` vem com a flag AD.
- **Domínio de e-mail**: SPF, DMARC e CAA são consultados no domínio do site sem o `www.` (ex.: `www.recife.pe.gov.br` vira `recife.pe.gov.br`).
- **TLS antigo**: um único handshake oferecendo só TLS 1.0 e 1.1, sem nenhuma requisição HTTP depois. É o mesmo teste que ferramentas como o SSL Labs fazem.
- **Página inicial**: lemos até 512 KB do HTML da página final (depois dos redirecionamentos) para os itens de conteúdo misto e headers. A página é baixada uma vez só.
- **Limite por servidor**: muitas prefeituras ficam hospedadas no mesmo servidor. A varredura verifica no máximo 3 sites por IP ao mesmo tempo e embaralha a ordem da lista, para não sobrecarregar ninguém.
- **Repescagem**: no fim da varredura, quem teve timeout é verificado de novo, com mais tempo (25 s por conexão) e uma prefeitura por servidor de cada vez.

## Limitações conhecidas

- A lista de domínios depende do Wikidata. Município sem site cadastrado lá não entra.
- Alguns servidores bloqueiam IPs de datacenter (como os do GitHub Actions), o que pode gerar `error` em vez do resultado real.
- O DMARC é lido só no próprio domínio. Ainda não consideramos a política herdada do domínio organizacional ([RFC 7489, seção 6.6.3](https://www.rfc-editor.org/rfc/rfc7489#section-6.6.3)).
- Conteúdo misto e cookies olham só a página inicial, não o site inteiro.
- Um site pode ter nota boa e ainda assim ter vulnerabilidades. O farol mede higiene de configuração, não faz pentest.

## Mudanças

**Versão 2 (16/11/2026)**
- Itens novos: `tls_antigo`, `conteudo_misto`, `cookies` e `caa`. Total de pontos passou de 16 para 20.
- `https` vira parcial quando o certificado vence em menos de 14 dias.
- Item não verificado (`error`) deixa de valer zero e sai da conta.
- DNS com mais resolvers e nova tentativa; limite de conexões por servidor; repescagem de timeouts. Na varredura de 16/11, feita ainda com a versão 1, cerca de 800 cidades tiveram SPF, DMARC ou DNSSEC sem resposta por sobrecarga nos resolvers.

**Versão 1 (13/11/2026)**: primeira versão, com 9 itens.
