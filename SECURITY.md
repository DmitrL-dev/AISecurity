# Security Policy

## Reporting a Vulnerability

**DO NOT** open a public GitHub issue for security vulnerabilities.

### Private Disclosure

**Email:** chg@live.ru

**Telegram:** [@DmLabincev](https://t.me/DmLabincev)

**Include:**
- Description of the vulnerability
- Steps to reproduce
- Affected component (sentinel-core, shield, brain, etc.)
- Potential impact
- Your suggested fix (optional)

### Response Timeline

| Stage | Timeframe |
|-------|-----------|
| Acknowledgment | 48 hours |
| Initial assessment | 1 week |
| Fix development | 7-30 days |
| Public disclosure | After fix is released |

### Process

1. **Acknowledgment** — We confirm receipt
2. **Assessment** — We evaluate severity and impact
3. **Communication** — We keep you updated
4. **Fix** — We develop and test a patch
5. **Release** — We publish the fix
6. **Credit** — We credit you (if desired) in commit history

---

## Security Best Practices

### API Keys

```python
# Never hardcode credentials
import os
api_key = os.environ.get("SENTINEL_API_KEY")
```

### Production Deployment

```bash
# 1. Set strong secrets in .env
cp .env.example .env
# Edit .env — change all placeholder values

# 2. Use docker-compose with restricted ports
docker-compose up -d

# 3. Run behind a reverse proxy (nginx/caddy) with TLS
```

### Prompt Data

Sentinel scans prompts but does **not** store them by default. For privacy compliance, configure:

```yaml
logging:
  include_prompts: false
  hash_only: true
```

---

## Scope

This security policy covers:

| Component | Language | Notes |
|-----------|----------|-------|
| [sentinel-core](./sentinel-core) | Rust | 61 detection engines — core attack surface |
| [brain](./src/brain) | Python | API backend — network-facing |
| [shield](./shield) | C11 | DMZ — memory safety critical |
| [immune](./immune) | C | EDR — kernel-level, highest severity |
| [strike](./strike) | Python | Red team tools — handle with care |

---

## Known Considerations

- `signatures/jailbreaks.json` is ~51 MB. If you fork, consider Git LFS.
- The `strike/` directory contains real attack payloads (39K+). Treat as sensitive.
- Docker images should not be exposed to public internet without a TLS reverse proxy.

---

## Contact

- **Security issues:** chg@live.ru
- **General:** [GitHub Issues](https://github.com/DmitrL-dev/AISecurity/issues)
- **Telegram:** [@DmLabincev](https://t.me/DmLabincev)

---

*Last updated: February 2026*
