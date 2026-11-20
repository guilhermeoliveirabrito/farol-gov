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
| `versao_exposta` | 0 | Nem os headers `Server`/`X-Powered-By`/`X-AspNet-Version` nem o `<meta name="generator">` da página mostram número de versão (ex.: `Apache/2.4.29`, `PHP/7.4.3`, `WordPress 6.4.3`) | - |
| `dnssec` | 2 | Resolver validador marca a resposta com o bit AD | - |
| `caa` | 1 | Existe registro CAA `issue`/`issuewild` no domínio ou em um domínio acima (ex.: `sp.gov.br`) | - |
| `spf` | 1 | Registro `v=spf1` terminando em `-all` ou `~all` | `?all` ou sem mecanismo `all` |
| `dmarc` | 3 | `_dmarc` com `p=reject` ou `p=quarantine` | `p=none` |
| `email_tls` | 0 | `_mta-sts` com `v=STSv1` (MTA-STS: quem manda e-mail para a prefeitura tem que usar TLS válido) | Só TLS-RPT (`_smtp._tls`), que manda relatório mas não exige TLS |
| `privacidade` | 0 | A página inicial não carrega rastreador de terceiros (Google Analytics, Tag Manager, pixel do Facebook, Hotjar, Clarity...) **e** tem link para a política de privacidade / LGPD. Também anota se o encarregado de dados aparece na página | Só um dos dois |

Total: 20 pontos. `versao_exposta` e `email_tls` entraram na semana de 16/11 (metodologia 4) e `privacidade` na de 23/11; os três têm peso 0 e contam só como detalhe.

DMARC e HTTPS têm peso maior porque são os que mais afetam o cidadão diretamente: um protege contra golpe por e-mail em nome do órgão, o outro protege o que é digitado no site.

`conteudo_misto` considera falha grave (`fail`) scripts, iframes, folhas de estilo e formulários carregados por `http://`, porque eles permitem alterar a página. Links comuns (`<a href="http://...">`) não contam.

## Nota

A nota tem duas partes.

**Nota base (0 a 100)**: o essencial. É a conta de sempre, com os pesos da tabela acima:

```
nota = 100 * soma(peso * valor) / soma(pesos dos itens verificados)
```

Item cumprido vale 1, parcial vale 0,5 e não cumprido vale 0. Cada ponto de peso vale 5 da nota base (são 20 pontos de peso ao todo). É ela que define o conceito.

**Detalhes**: passos além do essencial, que valem pouco (de 0,1 a 1 ponto cada) e somam por cima da nota base no ranking. Não derrubam ninguém: quem não tem o detalhe só não ganha o ponto extra. Servem para separar quem fez o essencial igual.

| Detalhe | Pontos |
|---|---|
| TLS 1.3 | +1 |
| Content-Security-Policy na página | +1 |
| DMARC com p=reject: o e-mail falso é recusado, não vai para o spam | +1 |
| Não mostra a versão do servidor nem do sistema do site | +1 |
| MTA-STS: exige criptografia no e-mail enviado para a prefeitura | +1 |
| Poucos scripts de outros sites: cada site de fora tira 0,15 | +0,75 |
| Nenhum rastreador de terceiros (Google Analytics, pixel do Facebook...) na página inicial | +0,5 |
| Link para a política de privacidade / LGPD na página inicial | +0,5 |
| HSTS cobrindo os subdomínios | +0,5 |
| HSTS pronto para a lista de preload dos navegadores | +0,5 |
| Referrer-Policy: não vaza o endereço da página para outros sites | +0,5 |
| Permissions-Policy: desliga câmera, microfone e afins que o site não usa | +0,5 |
| DMARC mandando relatórios (rua=) | +0,5 |
| SPF terminando em -all: recusa quem não está na lista | +0,5 |
| CAA no próprio domínio, sem depender do registro do estado | +0,5 |
| TLS-RPT: recebe relatório quando o e-mail chega sem criptografia | +0,5 |
| Encarregado de dados (LGPD) indicado na página inicial | +0,25 |
| Sem jQuery antigo (anterior ao 3.5, com XSS conhecido) | +0,25 |
| HSTS longo: proporcional ao max-age, cheio a partir de 2 anos | +0,25 |
| Scripts de fora com SRI: o navegador recusa se alguém trocar o arquivo | +0,25 |
| CSP sem unsafe-inline nem unsafe-eval | +0,25 |
| Certificado de até 100 dias (renovação automática) | +0,25 |
| Site com IPv6 | +0,25 |
| Servidores DNS em pelo menos dois provedores | +0,25 |
| Cross-Origin-Opener-Policy: isola a página de janelas abertas por outros sites | +0,25 |
| Cookies com SameSite (ou nenhum cookie na página inicial) | +0,25 |
| security.txt com validade (Expires) | +0,25 |
| Não mostra nem o nome do software do servidor | +0,25 |
| Redirecionamento para HTTPS permanente (301/308): o navegador nem tenta mais o HTTP | +0,1 |
| Certificado vale com e sem www | +0,1 |
| Cross-Origin-Resource-Policy: outro site não embute os arquivos da prefeitura | +0,1 |
| Cross-Origin-Embedder-Policy | +0,1 |
| CAA proíbe certificado curinga (*.dominio) | +0,1 |
| DMARC com alinhamento estrito (adkim=s ou aspf=s) | +0,1 |
| CAA com iodef: avisa a prefeitura se alguém pedir certificado indevido | +0,1 |

Dois detalhes são graduais e dão parte dos pontos:

- **Scripts de outros sites**: 0,75 sem nenhum; cada site de fora de onde a página inicial puxa script tira 0,15 (1 site: 0,6; 3 sites: 0,3; 5 ou mais: 0). Cada um é mais alguém que, se for invadido, roda código na página da prefeitura.
- **HSTS longo**: proporcional ao `max-age`, até 0,25 com 2 anos ou mais (1 ano dá 0,12).

O jQuery é procurado no nome do arquivo (`jquery-1.12.4.min.js`), no `?ver=` do WordPress e no caminho de CDN (`/jquery/3.4.1/`). Quem carrega jQuery sem versão aparente não ganha o detalhe, porque não dá para saber se é antigo.

`versao_exposta`, `email_tls` e `privacidade` são verificados e aparecem na página, mas têm peso 0 na nota base: contam só como detalhe. Um deles sem resposta também não tira a cidade do ranking oficial, porque não mexe na nota.

Nas metodologias 3 e 4 (semana de 16/11), os detalhes descontavam da nota base. Isso derrubou as notas e foi desfeito na metodologia 5: a nota base voltou a ser a de antes e os detalhes passaram a somar. As semanas antigas não guardaram os detalhes, então nelas vale só a nota base.

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

- **Posição no Brasil**: ordem de nota base + detalhes entre as cidades que estão no ranking. Se ainda empatar, desempata por:
  1. mais itens cumpridos por inteiro (dois parciais somam o mesmo que um inteiro na nota, mas aqui valem menos);
  2. maior população, ou seja, mais gente protegida. Esse critério existe porque várias prefeituras ficam no mesmo servidor, com o site montado igual (24 de SE no servidor do governo do estado), e nenhum critério técnico consegue separá-las.
  Só cidades sem população conhecida e com tudo igual dividem a posição.
- **Variação**: diferença de posição em relação à semana anterior (a última varredura daquela semana). Se a varredura rodar de novo na mesma semana, a seta não compara as duas rodadas, porque a diferença entre elas não tem a ver com os sites. Quando entram itens novos entre uma semana e outra, a página avisa que parte do movimento vem deles. Como as notas têm poucos valores possíveis, muitas cidades empatam, e uma mudança pequena de nota ainda pode mover uma cidade muitas posições.
- **Histórico**: cada varredura completa é guardada em `data/historico/AAAA-MM-DD.json` (vale a última do dia), só com o status de cada item. O gráfico da página e o histórico de cada cidade mostram uma varredura por semana. **As notas das semanas antigas são recalculadas com as regras atuais**, para que a comparação faça sentido. Um item novo só entra na conta a partir da semana em que começou a ser verificado. No gráfico da página, a semana em que a metodologia mudou aparece marcada.

## Medalhas e hall da fama

- **Semana** vai de segunda a domingo, no horário de Brasília. Se houver mais de uma varredura na semana, vale só a última, do mesmo jeito que no histórico vale só a última varredura de cada dia.
- **Quem concorre:** só quem teve todos os itens verificados naquela varredura.
- **Pódio:** ouro, prata e bronze vão para o 1º, o 2º e o 3º do ranking, com a mesma ordem da posição (nota base + detalhes, itens inteiros, população). Quando o desempate decide uma medalha, o pódio mostra qual critério decidiu. Se duas cidades empatarem em tudo, dividem a medalha e a seguinte leva a próxima.
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
