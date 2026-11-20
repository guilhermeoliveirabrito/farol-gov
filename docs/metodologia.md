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

O site de cada município vem do Wikidata, e nem sempre o cadastro está certo. Na coleta, o farol confere a lista:

- aplica as correções revisadas à mão em `data/correcoes.csv`;
- quando o site do Wikidata é suspeito (fora do `.gov.br`, da câmara municipal, portal genérico), não existe no DNS ou nem foi cadastrado, procura o padrão oficial `<nome>.<uf>.gov.br` (e variações com `www.`, `pm` e `prefeitura`) e usa o que existir. Só órgão público registra `.gov.br`;
- tudo que foi trocado fica em `data/dominios_corrigidos.csv`, com o motivo.

Na varredura, mais algumas checagens:

| Aviso | O que acontece |
|---|---|
| `dominio_alternativo` | O domínio cadastrado não existe, mas a versão com/sem `www.` existe. Avaliamos a que funciona. |
| `nao_resolve` | Nenhuma das duas versões existe no DNS. Fica sem nota. |
| `fora_do_gov_br` | O domínio não termina em `.gov.br` e não está em `data/correcoes.csv`. É avaliado, mas fica **fora do ranking** até alguém confirmar que é mesmo o site da prefeitura (já apareceu site de associação de municípios cadastrado como site de prefeitura). |
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
| `versao_exposta` | 1 | Nem os headers `Server`/`X-Powered-By`/`X-AspNet-Version` nem o `<meta name="generator">` da página mostram número de versão (ex.: `Apache/2.4.29`, `PHP/7.4.3`, `WordPress 6.4.3`) | - |
| `dnssec` | 2 | Resolver validador marca a resposta com o bit AD | - |
| `caa` | 1 | Existe registro CAA `issue`/`issuewild` no domínio ou em um domínio acima (ex.: `sp.gov.br`) | - |
| `spf` | 1 | Registro `v=spf1` terminando em `-all` ou `~all` | `?all` ou sem mecanismo `all` |
| `dmarc` | 3 | `_dmarc` com `p=reject` ou `p=quarantine` | `p=none` |
| `email_tls` | 1 | `_mta-sts` com `v=STSv1` (MTA-STS: quem manda e-mail para a prefeitura tem que usar TLS válido) | Só TLS-RPT (`_smtp._tls`), que manda relatório mas não exige TLS |

Total: 22 pontos. `versao_exposta` e `email_tls` entraram na semana de 16/11 (metodologia 4).

DMARC e HTTPS têm peso maior porque são os que mais afetam o cidadão diretamente: um protege contra golpe por e-mail em nome do órgão, o outro protege o que é digitado no site.

`conteudo_misto` considera falha grave (`fail`) scripts, iframes, folhas de estilo e formulários carregados por `http://`, porque eles permitem alterar a página. Links comuns (`<a href="http://...">`) não contam.

## Nota

```
nota = 100 * soma(peso * grau) / soma(pesos dos itens verificados)
```

O **grau** vai de 0 a 1, em passos de 0,05. Item não cumprido vale 0. Item parcial (`warn`) vale 0,5, menos três casos em que o parcial é fraco e vale 0,3: DMARC com `p=none` (só monitora), SPF com `?all` ou sem `all` (não bloqueia nada) e só um dos dois headers básicos.

Item cumprido vale 1, menos quando para no mínimo:

| Item | Desconto |
|---|---|
| `tls` | TLS 1.2 em vez de 1.3: −0,2 |
| `hsts` | sem `includeSubDomains`: −0,2; sem `preload`: −0,1; `max-age` menor que 2 anos: −0,1 |
| `headers` | sem Content-Security-Policy: −0,2; sem Referrer-Policy: −0,1; sem Permissions-Policy: −0,1 |
| `dmarc` | `p=quarantine` em vez de `p=reject`: −0,15; sem relatórios (`rua=`): −0,1 |
| `spf` | `~all` em vez de `-all`: −0,2 |
| `caa` | registro herdado do domínio do estado, não do próprio: −0,2 |
| `cookies` | algum cookie sem `SameSite`: −0,1 |
| `security_txt` | sem o campo `Expires`, obrigatório pela RFC 9116: −0,2 |
| `versao_exposta` | mostra o nome do software, mesmo sem a versão: −0,1 |
| `email_tls` | MTA-STS sem TLS-RPT: −0,2 |
| `dmarc` (de novo) | `pct=` menor que 100, a política só vale para parte dos e-mails: −0,1 |

Os parciais também têm graus: `cookies` vale de 0,3 a 0,7 conforme a proporção de cookies sem `HttpOnly`, e `conteudo_misto` vale 0,7 com uma imagem por `http://`, 0,5 com até três e 0,3 com mais.

Até a metodologia 2, todo item cumprido valia o cheio. Com 13 itens a nota tinha umas 30 combinações possíveis: na varredura de 19/11 eram 565 cidades com a mesma nota e 29 empatadas no topo. Com os graus passam de 200 notas diferentes. As semanas antigas guardaram só o status de cada item, então nelas o item cumprido continua valendo 1.

| Conceito | Nota |
|---|---|
| A | >= 90 |
| B | >= 75 |
| C | >= 55 |
| D | >= 35 |
| F | < 35 |

## Quem entra no ranking

- Só entram as prefeituras com todos os itens daquela varredura verificados. Dele saem as posições, as setas de quem subiu ou caiu e as medalhas.
- Quem teve algum item sem resposta continua na lista, no fim e sem posição. Item não verificado sai da conta da nota, então a nota dessa cidade é calculada sobre menos itens e pode ficar acima da real.
- Médias, adoção de cada item e o gráfico semana a semana usam todas as prefeituras com nota.

## Posição e histórico

- **Posição no Brasil**: ordem das notas entre as cidades que estão no ranking. Nota igual desempata, nesta ordem, por:
  1. mais itens cumpridos por inteiro (dois parciais somam o mesmo que um inteiro na nota, mas aqui valem menos);
  2. mais pontos de excelência: DMARC com `p=reject`, DMARC mandando relatórios (`rua=`), SPF com `-all`, TLS 1.3, HSTS com `includeSubDomains`, HSTS com `preload`, HSTS de 2 anos ou mais, Content-Security-Policy, Referrer-Policy, Permissions-Policy e CAA no próprio domínio;
  3. maior população, ou seja, mais gente protegida. Esse critério existe porque várias prefeituras ficam no mesmo servidor, com o site montado igual (24 de SE no servidor do governo do estado), e nenhum critério técnico consegue separá-las.
  Só cidades sem população conhecida e com tudo igual dividem a posição.
- **Variação**: diferença de posição em relação à semana anterior (a última varredura daquela semana). Se a varredura rodar de novo na mesma semana, a seta não compara as duas rodadas, porque a diferença entre elas não tem a ver com os sites. Quando entram itens novos entre uma semana e outra, a página avisa que parte do movimento vem deles. Como as notas têm poucos valores possíveis, muitas cidades empatam, e uma mudança pequena de nota ainda pode mover uma cidade muitas posições.
- **Histórico**: cada varredura completa é guardada em `data/historico/AAAA-MM-DD.json` (vale a última do dia), só com o status de cada item. O gráfico da página e o histórico de cada cidade mostram uma varredura por semana. **As notas das semanas antigas são recalculadas com as regras atuais**, para que a comparação faça sentido. Um item novo só entra na conta a partir da semana em que começou a ser verificado. No gráfico da página, a semana em que a metodologia mudou aparece marcada.

## Medalhas e hall da fama

- **Semana** vai de segunda a domingo, no horário de Brasília. Se houver mais de uma varredura na semana, vale só a última, do mesmo jeito que no histórico vale só a última varredura de cada dia.
- **Quem concorre:** só quem teve todos os itens verificados naquela varredura.
- **Pódio:** ouro, prata e bronze vão para o 1º, o 2º e o 3º do ranking, com o mesmo desempate da posição (itens inteiros, pontos de excelência, população). Quando o desempate decide uma medalha, o pódio mostra qual critério decidiu. Se duas cidades empatarem em tudo, dividem a medalha e a seguinte leva a próxima.
- **Semana em andamento:** o pódio da semana atual aparece como parcial até domingo, porque uma nova varredura ainda pode mudá-lo.
- **Hall da fama:** ouro vale 10 pontos, prata 5 e bronze 2,5. Em empate de pontos, fica na frente quem tem mais ouros e depois quem tem mais pratas. Se tudo empatar, as cidades dividem a posição.
- As notas de semanas antigas são recalculadas com as regras atuais, então as medalhas de semanas passadas também seguem a metodologia de hoje.

## Como a varredura se protege de uma rodada ruim

- **Uma fila por servidor.** Muitas prefeituras ficam no mesmo servidor de hospedagem. Primeiro o farol consulta o DNS de todas, depois visita os sites com no máximo 3 conexões simultâneas por servidor. Um servidor lento atrasa só as cidades dele, não a varredura inteira.
- **Prazos.** Cada página tem um tempo máximo de leitura, a varredura tem 90 minutos e a repescagem de quem deu timeout tem mais 20. Se o prazo acaba antes de visitar algum site, aquela cidade fica sem nota só nesta rodada, com o aviso de verificação incompleta. Ela não some da lista.
- **DNS em dois caminhos.** O endereço do site é consultado primeiro nos resolvers públicos que validam DNSSEC (Cloudflare, Google, Quad9), porque é dessa resposta que sai a flag de DNSSEC. Os outros registros (SPF, DMARC, CAA) vão primeiro para o resolver do próprio servidor da varredura, que é mais rápido e não limita o número de consultas. Se um caminho não responde, a consulta vai pelo outro; quando só o resolver do servidor responde o endereço, o DNSSEC fica como não verificado. No fim, quem ficou com algum item de DNS sem resposta tem só o DNS consultado de novo.
- **CAA sem resposta.** Se o DNS da prefeitura responde o endereço do site mas não responde a consulta CAA (alguns servidores antigos ignoram tipos de registro que não conhecem), o item conta como não cumprido. Na prática as autoridades certificadoras também não conseguem ler a política.
- **Validação antes de publicar.** Antes de ir para o histórico e para o site, a rodada é comparada com a anterior. Se muito menos sites responderam (menos de 90%), se mais de 8% ficaram com verificação incompleta ou se o prazo deixou mais de 2% sem visita, nada é publicado: o site continua com a varredura anterior e o motivo aparece no resumo do GitHub Actions.

## Detalhes técnicos

- **DNS**: consultas em cinco resolvers públicos que validam DNSSEC (Cloudflare, Google e Quad9), com rodízio entre eles, 3 segundos por servidor, até 12 segundos por consulta e uma nova tentativa quando dá timeout. O DNSSEC é considerado válido quando a resposta para o registro `A` vem com a flag AD.
- **Domínio de e-mail**: SPF, DMARC, CAA e MTA-STS são consultados no domínio do site sem o `www.` (ex.: `www.recife.pe.gov.br` vira `recife.pe.gov.br`).
- **TLS antigo**: um único handshake oferecendo só TLS 1.0 e 1.1, sem nenhuma requisição HTTP depois. É o mesmo teste que ferramentas como o SSL Labs fazem. Se o servidor fica sem responder por 6 segundos (comum em firewall que descarta versões antigas), conta como recusa: ele já tinha respondido ao handshake moderno logo antes, então está no ar e simplesmente não fala TLS 1.0.
- **Página inicial**: lemos até 512 KB do HTML da página final (depois dos redirecionamentos) para os itens de conteúdo misto e headers. A página é baixada uma vez só.
- **Limite por servidor**: muitas prefeituras ficam hospedadas no mesmo servidor. A varredura verifica no máximo 3 sites por IP ao mesmo tempo e embaralha a ordem da lista, para não sobrecarregar ninguém.
- **Repescagem**: no fim da varredura, quem teve timeout é verificado de novo, com mais tempo (25 s por conexão) e uma prefeitura por servidor de cada vez.

## Limitações conhecidas

- A lista de domínios parte do Wikidata. Município sem site lá só entra se o padrão `<nome>.<uf>.gov.br` existir; quem usa outro endereço precisa de uma linha em `data/correcoes.csv`.
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
