# Clawdbot Security Rules

> Правила безопасности для интеграции с Clawdbot и подобными AI-агентами

## Mandatory Settings

Эти настройки ОБЯЗАТЕЛЬНЫ для безопасной работы:

```yaml
# clawdbot-config.yaml (или аналог)

browser:
  evaluateEnabled: false     # ← КРИТИЧНО! Отключаем eval()
  screenshotEnabled: true    # Разрешено
  navigationEnabled: true    # Разрешено

tools:
  exec:
    enabled: true
    security: allowlist      # deny | allowlist | full
    ask: always              # never | on-miss | always
    host: sandbox            # native | docker | sandbox
    
    # Лимиты
    timeout: 30              # секунд
    maxConcurrent: 3
    
    # Whitelist безопасных команд
    allowlist:
      - npm
      - node
      - python
      - git
      - ls
      - cat
      - grep
    
    # Blocklist опасных паттернов
    blocklist:
      - rm -rf
      - ":(){ :|:& };:"
      - curl * | sh
      - wget * | sh
      - eval
      - exec

  fileAccess:
    deniedPaths:
      - ~/.ssh
      - ~/.aws
      - ~/.gnupg
      - ~/.config/gcloud
      - ~/.azure
      - ~/.kube
      - /etc/passwd
      - /etc/shadow

gateway:
  rateLimit:
    enabled: true
    maxRequests: 100         # per minute
    windowMs: 60000
  
  cors:
    enabled: true
    origins:
      - http://localhost:*
  
  csrf:
    enabled: true
```

---

## Blocked Patterns

### Category A: Remote Code Execution

| Pattern | Risk | Block |
|---------|------|-------|
| `eval(` | Critical | ✅ |
| `Function(` | Critical | ✅ |
| `:(){ :|:& };:` | Critical | ✅ |
| `bash -i >& /dev/tcp` | Critical | ✅ |
| `nc -e /bin/sh` | Critical | ✅ |
| `curl \| sh` | Critical | ✅ |

### Category B: Credential Exfiltration

| Pattern | Risk | Block |
|---------|------|-------|
| `~/.ssh/id_rsa` | Critical | ✅ |
| `~/.aws/credentials` | Critical | ✅ |
| `~/.gnupg/` | Critical | ✅ |
| `/etc/passwd` | High | ✅ |
| `$OPENAI_API_KEY` | High | ✅ |

### Category C: Persistence

| Pattern | Risk | Block |
|---------|------|-------|
| `crontab -` | High | ✅ |
| `schtasks /create` | High | ✅ |
| `.bashrc` write | Medium | ⚠️ |
| `~/.profile` write | Medium | ⚠️ |

---

## Financial Limits

```yaml
financial:
  enabled: true
  maxAutoAmount: 50          # USD, auto-approve below this
  requireApproval: true
  
  blockedCategories:
    - masterminds
    - coaching
    - premium-domains
    - crypto-trading
    - gambling
  
  approvedVendors:
    - npm
    - pypi
    - github
    - vercel
    - netlify
```

---

## Rate Limiting

```yaml
rateLimits:
  exec:
    perMinute: 30
    perHour: 300
  
  llm:
    perMinute: 60
    perHour: 1000
  
  browser:
    perMinute: 20
    perHour: 200
  
  file:
    writesPerMinute: 50
    deletesPerMinute: 10
```

---

## Audit Logging

```yaml
audit:
  enabled: true
  logPath: ~/.sentinel/audit.log
  
  logEvents:
    - exec.command
    - exec.blocked
    - file.write
    - file.delete
    - browser.eval
    - financial.attempt
    - financial.blocked
  
  retention: 90              # days
  immutable: true            # append-only
```

---

## Enforcement

### Pre-commit Hook

Добавить в `.git/hooks/pre-commit`:

```bash
# Check for eval()
if grep -r "eval(" src/; then
    echo "❌ eval() detected - blocked by Sentinel"
    exit 1
fi
```

### CI/CD Gate

```yaml
# .github/workflows/security.yml
- name: Sentinel Security Check
  run: |
    sentinel-cli check --rules clawdbot-security
```

---

## Domains for RLM

| Domain | Level | Purpose |
|--------|-------|---------|
| `clawdbot-security` | L2 | Security findings |
| `clawdbot-financial` | L1 | Financial attempts |
| `clawdbot-blocked` | L1 | Blocked commands |
| `clawdbot-audit` | L1 | Audit events |
