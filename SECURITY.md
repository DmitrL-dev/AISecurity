# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 4.1.x   | ✅ Active          |
| 4.0.x   | ✅ Security fixes  |
| 3.x.x   | ❌ End of life     |
| < 3.0   | ❌ Not supported   |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly.

### 🔒 Private Disclosure (Preferred)

**DO NOT** open a public GitHub issue for security vulnerabilities.

**Email:** security@sentinel.ai

**PGP Key:** [Available on request]

**Include:**
- Description of the vulnerability
- Steps to reproduce
- Affected versions
- Potential impact
- Your suggested fix (optional)

### Response Timeline

| Stage | Timeframe |
|-------|-----------|
| Acknowledgment | 24 hours |
| Initial assessment | 72 hours |
| Fix development | 7-30 days |
| Public disclosure | After fix |

### What to Expect

1. **Acknowledgment** — We confirm receipt within 24 hours
2. **Assessment** — We evaluate severity and impact
3. **Communication** — We keep you updated on progress
4. **Fix** — We develop and test a patch
5. **Release** — We publish the fix
6. **Credit** — We credit you (if desired) in release notes

## Security Best Practices

When using SENTINEL:

### API Keys
```python
# ❌ Never hardcode
api_key = "sk-1234..."

# ✅ Use environment variables
import os
api_key = os.environ.get("SENTINEL_API_KEY")
```

### Production Deployment
```yaml
# ✅ Enable all security features
sentinel:
  api_key_required: true
  rate_limit: 1000
  tls_enabled: true
  audit_logging: true
```

### Dependencies
```bash
# ✅ Regularly update
pip install --upgrade sentinel-llm-security

# ✅ Audit dependencies
pip-audit
```

## Known Security Considerations

### Prompt Data

SENTINEL scans prompts but does **not** store them by default. For compliance:

```yaml
# Disable logging of prompt content
logging:
  include_prompts: false
  hash_only: true
```

### Model Endpoints

When using external LLM APIs:
- Use TLS for all connections
- Rotate API keys regularly
- Monitor for anomalous usage

## Bug Bounty

We currently do not have a formal bug bounty program. However, we recognize and credit security researchers who responsibly disclose vulnerabilities.

## Security Advisories

Security advisories are published on:
- [GitHub Security Advisories](https://github.com/DmitrL-dev/AISecurity/security/advisories)
- [CHANGELOG.md](./docs/CHANGELOG.md)

## Contact

- **Security issues:** security@sentinel.ai
- **General questions:** info@sentinel.ai
- **Discord:** [SENTINEL Community](https://discord.gg/sentinel)

---

*Last updated: January 18, 2026*
