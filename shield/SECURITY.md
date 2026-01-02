# SECURITY.md - Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in SENTINEL Shield, please:

1. **Do NOT** open a public issue
2. Email security@sentinel-ai.dev with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Your suggested fix (optional)

We will respond within 48 hours and aim to release a patch within 7 days for critical issues.

## Security Measures

SENTINEL Shield implements multiple layers of security:

### Input Validation

- All inputs are validated and sanitized
- Buffer sizes are strictly enforced
- Regex patterns are compiled with safety limits

### Memory Safety

- No dynamic memory allocation in hot paths
- Fixed-size buffers with overflow protection
- Careful use of strncpy/snprintf

### Authentication

- API endpoints support token authentication
- CLI supports privilege levels
- Audit logging of all administrative actions

### Network Security

- TLS support for protocols
- Rate limiting to prevent DoS
- Configurable network interfaces

### Code Quality

- Static analysis with clang-analyzer
- Address sanitizer testing
- Fuzz testing of parsers

## Security Hardening

For production deployments:

1. **Run as non-root user**

   ```bash
   useradd -r -s /bin/false sentinel
   chown -R sentinel:sentinel /etc/sentinel
   ```

2. **Restrict file permissions**

   ```bash
   chmod 600 /etc/sentinel/shield.conf
   chmod 600 /var/log/sentinel/*
   ```

3. **Enable seccomp (Linux)**
   Shield uses minimal syscalls; consider seccomp filtering

4. **Network isolation**

   - API should be behind reverse proxy
   - HA traffic should be on private network

5. **Regular updates**
   Check for security updates regularly

## Threat Model

SENTINEL Shield protects against:

1. **Prompt Injection** - Malicious prompts attempting to override system instructions
2. **Jailbreaking** - Attempts to bypass safety measures
3. **Data Exfiltration** - Leaking sensitive data through LLM responses
4. **DoS Attacks** - Rate limiting and resource management
5. **Supply Chain** - Minimal dependencies, verified builds

Shield does NOT protect against:

- Zero-day LLM vulnerabilities
- Server-side compromise
- Physical access attacks

## Compliance

SENTINEL Shield can help with:

- OWASP Top 10 for LLMs
- SOC 2 audit logging requirements
- GDPR data protection (with canary tokens)
- PCI-DSS sensitive data detection
