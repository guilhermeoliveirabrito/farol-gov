# farol-gov

**An open observatory of the security hygiene of Brazilian government websites and email domains.**

[Versão em português](README.md)

Every week, farol-gov checks whether the domains of Brazilian city halls, state governments and public agencies follow basic internet security standards: real HTTPS, modern TLS, DNSSEC and protection against spoofed email (SPF and DMARC). Results are published as open data and as a ranking by state and municipality.

## Checks

| Check | What it looks at |
|---|---|
| `https` | Site answers over HTTPS with a valid certificate |
| `redirect` | `http://` redirects to `https://` |
| `tls` | Negotiated protocol is TLS 1.2 or 1.3 |
| `hsts` | `Strict-Transport-Security` with max-age of at least one year |
| `headers` | `X-Content-Type-Options` and clickjacking protection |
| `security_txt` | `/.well-known/security.txt` with a contact |
| `dnssec` | DNS answers for the domain are DNSSEC-validated |
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

## License

Code: MIT. Data in `data/`: CC BY 4.0.
