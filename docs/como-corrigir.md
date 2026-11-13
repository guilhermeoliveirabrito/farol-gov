# Como corrigir cada item

Guia rápido para quem cuida do site ou do e-mail de uma prefeitura. Cada seção corresponde a um item verificado pelo farol-gov. Os exemplos usam Nginx e Apache, que são os mais comuns; se o site fica numa plataforma terceirizada, peça ao fornecedor o equivalente.

Depois de corrigir, você pode conferir na hora com `farol check seu.dominio.gov.br` ou no [TOP do NIC.br](https://top.nic.br/).

## https

**O problema:** o site não responde em HTTPS ou o certificado é inválido (vencido, autoassinado ou emitido para outro nome).

**Como resolver:** emita um certificado gratuito com [Let's Encrypt](https://letsencrypt.org/pt-br/getting-started/) usando o `certbot`, que também configura a renovação automática:

```bash
sudo certbot --nginx -d prefeitura.uf.gov.br -d www.prefeitura.uf.gov.br
```

Certificado vencido quase sempre é renovação manual esquecida. Automatize.

## redirect

**O problema:** quem digita o endereço sem `https://` continua navegando sem criptografia.

**Nginx:**

```nginx
server {
    listen 80;
    server_name prefeitura.uf.gov.br www.prefeitura.uf.gov.br;
    return 301 https://$host$request_uri;
}
```

**Apache:**

```apache
<VirtualHost *:80>
    ServerName prefeitura.uf.gov.br
    Redirect permanent / https://prefeitura.uf.gov.br/
</VirtualHost>
```

## tls

**O problema:** o servidor só negocia TLS 1.0 ou 1.1, que estão obsoletos desde a [RFC 8996](https://www.rfc-editor.org/rfc/rfc8996).

**Nginx:** `ssl_protocols TLSv1.2 TLSv1.3;`

**Apache:** `SSLProtocol -all +TLSv1.2 +TLSv1.3`

O [gerador de configuração da Mozilla](https://ssl-config.mozilla.org/) monta o bloco completo para o seu servidor.

## hsts

**O problema:** sem HSTS, um atacante na mesma rede (Wi-Fi público, por exemplo) consegue forçar o navegador a usar HTTP.

**Como resolver:** depois que o HTTPS estiver funcionando em tudo, adicione o header. Comece com um valor baixo e aumente para 1 ano quando tiver certeza de que nada quebrou:

```nginx
add_header Strict-Transport-Security "max-age=31536000" always;
```

Cuidado com `includeSubDomains`: só use se **todos** os subdomínios tiverem HTTPS.

## headers

**O problema:** faltam proteções baratas contra ataques comuns no navegador.

```nginx
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "SAMEORIGIN" always;
```

```apache
Header always set X-Content-Type-Options "nosniff"
Header always set X-Frame-Options "SAMEORIGIN"
```

`X-Frame-Options` impede que o site seja carregado dentro de um iframe em outro domínio (clickjacking). Quem já usa Content-Security-Policy pode usar `frame-ancestors 'self'` no lugar.

## security_txt

**O problema:** um pesquisador que encontra uma falha no site não sabe para quem avisar.

**Como resolver:** crie o arquivo `/.well-known/security.txt` ([RFC 9116](https://www.rfc-editor.org/rfc/rfc9116)), servido como `text/plain`:

```
Contact: mailto:seguranca@prefeitura.uf.gov.br
Expires: 2027-12-31T23:59:00.000Z
Preferred-Languages: pt, en
```

O campo `Expires` é obrigatório. Lembre de atualizar a data antes de vencer.

## dnssec

**O problema:** sem DNSSEC, respostas de DNS podem ser falsificadas e o cidadão pode ser levado a um servidor falso.

**Como resolver:** são duas etapas. Quem hospeda o DNS do domínio assina a zona, e a zona "de cima" publica um registro DS apontando para a chave.

- **Domínio registrado direto no Registro.br** (ex.: `prefeitura.gov.br`, `cidade.com.br`): se o DNS for o do próprio Registro.br, o DNSSEC já vem ativado. Se for outro provedor (Cloudflare, hospedagem, servidor próprio), ative a assinatura lá e cadastre o DS no painel do Registro.br.
- **Subdomínio do estado** (ex.: `cidade.pe.gov.br`, o caso da maioria das prefeituras): o DS precisa ser publicado na zona do estado (`pe.gov.br`), que é administrada pelo governo estadual. Assine a sua zona e peça ao órgão de TI do estado para publicar o DS. Isso explica parte da baixa adoção: depende de duas equipes diferentes.

Os [tutoriais de DNS e DNSSEC do Registro.br](https://registro.br/tecnologia/dnssec/tutoriais/) explicam a parte técnica. Atenção: DS errado ou assinatura vencida deixam o domínio **fora do ar** para quem usa resolvedor validador, então teste antes com o [DNSViz](https://dnsviz.net/).

## spf

**O problema:** não há uma lista de servidores autorizados a enviar e-mail em nome do domínio.

**Como resolver:** publique um registro TXT no domínio com todos os serviços que enviam e-mail por vocês (servidor próprio, Google Workspace, Microsoft 365, sistema de nota fiscal etc.) e termine com `-all` ou `~all`:

```
prefeitura.uf.gov.br.  TXT  "v=spf1 include:_spf.google.com include:spf.protection.outlook.com -all"
```

- Só pode existir **um** registro SPF por domínio.
- Nunca use `+all`: ele autoriza qualquer servidor do mundo.
- O SPF tem limite de 10 consultas de DNS (`include`, `a`, `mx`...). Passou disso, ele quebra.

## dmarc

**O problema:** sem DMARC com política de bloqueio, qualquer pessoa consegue mandar e-mail "da prefeitura" e ele chega na caixa de entrada. É o golpe mais comum contra servidores e cidadãos.

**Como resolver**, em etapas para não bloquear e-mail legítimo:

1. Comece só monitorando, recebendo relatórios:
   ```
   _dmarc.prefeitura.uf.gov.br.  TXT  "v=DMARC1; p=none; rua=mailto:dmarc@prefeitura.uf.gov.br"
   ```
2. Durante algumas semanas, leia os relatórios e corrija SPF e DKIM dos serviços legítimos que aparecerem falhando.
3. Suba para `p=quarantine` (vai para o spam).
4. Quando estiver tranquilo, `p=reject`.

No farol-gov, `p=none` conta como parcial: é um bom começo, mas ainda não protege ninguém.
