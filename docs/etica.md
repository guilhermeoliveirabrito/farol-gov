# Ética e limites do projeto

O objetivo do farol-gov é dar transparência e incentivar melhorias, não expor órgãos a ataques. Por isso o projeto segue algumas regras fixas.

## Só verificações passivas

Para cada domínio fazemos apenas:

- consultas DNS públicas (`A`, `TXT`, `_dmarc`);
- uma conexão TLS na porta 443;
- requisições `GET` para `/` (em HTTP e HTTPS) e para `/.well-known/security.txt`, que é um caminho feito justamente para ser lido por terceiros.

Isso é o mesmo que um navegador ou um servidor de e-mail faz todos os dias.

## O que nunca fazemos

- varredura de portas;
- detecção de versão de software ou de CVEs;
- testes em caminhos sensíveis (`/.git`, `/admin`, backups etc.);
- qualquer tentativa de login, injeção ou envio de formulário.

## O que publicamos

Só itens de **higiene de configuração**, que qualquer pessoa consegue checar com ferramentas públicas como o [TOP do NIC.br](https://top.nic.br/). Não publicamos nada que funcione como "mapa" para explorar um sistema.

## Identificação

Todas as requisições HTTP usam o User-Agent `farol-gov/<versão> (+https://github.com/guilhermeoliveirabrito/farol-gov)`, para que qualquer administrador saiba de onde veio o acesso.

## Contestação e remoção

Se você é responsável por algum domínio e acha que o resultado está errado, ou quer que ele seja removido, abra uma issue. Resultados contestados são revisados manualmente.
