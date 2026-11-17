# farol-gov

**An open observatory of the security hygiene of Brazilian government websites and email domains.**

[Versão em português](README.md)

Every week, farol-gov checks whether the domains of Brazilian city halls, state governments and public agencies follow basic internet security standards: real HTTPS, modern TLS, DNSSEC and protection against spoofed email (SPF and DMARC). Results are published as open data, as a ranking by state and municipality, and as a weekly history showing which cities moved up or down.

## Checks

| Check | What it looks at |
|---|---|
| `https` | Site answers over HTTPS with a valid certificate |
| `redirect` | `http://` redirects to `https://` |
| `tls` | Negotiated protocol is TLS 1.2 or 1.3 |
| `tls_antigo` | Server refuses TLS 1.0 and 1.1 handshakes |
| `hsts` | `Strict-Transport-Security` with max-age of at least one year |
| `headers` | `X-Content-Type-Options` and clickjacking protection |
| `conteudo_misto` | HTTPS home page loads nothing over `http://` |
| `cookies` | Cookies set with `Secure` and `HttpOnly` |
| `security_txt` | `/.well-known/security.txt` with a contact |
| `dnssec` | DNS answers for the domain are DNSSEC-validated |
| `caa` | CAA record restricting which CAs may issue certificates |
| `spf` | SPF record that does not allow any sender |
| `dmarc` | DMARC policy set to `quarantine` or `reject` |

Weights and scoring: [docs/metodologia.md](docs/metodologia.md) (Portuguese).

## Passive only

All checks are passive: public DNS lookups, one TLS handshake and a plain `GET` to the home page, the same thing any browser does. No port scanning, no vulnerability probing, no brute force.

## Quick start

```bash
pip install -e ".[dev]"
farol check www.recife.pe.gov.br
```

## Open data

Everything on the page comes from static JSON files you can use directly (CC BY 4.0): [`dados/latest.json`](https://guilhermeoliveirabrito.github.io/farol-gov/dados/latest.json) has the full latest scan, [`dados/historico.json`](https://guilhermeoliveirabrito.github.io/farol-gov/dados/historico.json) the national series, and `dados/uf/<UF>.json` the per-state details. Each city also has a self-updating SVG badge at `selos/<IBGE code>.svg`.

## License

Code: MIT. Data in `data/`: CC BY 4.0.
