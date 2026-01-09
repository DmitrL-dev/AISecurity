# Requirements: MCP OAuth Validation

## Обзор

Расширение MCPSecurityMonitor для детекции небезопасного credential management в MCP серверах.

## Источник угрозы

- **Статистика:** 43% MCP серверов уязвимы к command injection, 53% используют static credentials
- **CVE:** CVSS 7.3-9.6
- **OWASP:** ASI03 — Excessive Permissions, ASI04 — Unbounded Tool Access

---

## Функциональные требования

### REQ-MO-001: Static credential detection
**EARS:** WHEN MCP конфигурация содержит hardcoded API keys, THEN система ДОЛЖНА флаговать как high risk.

Patterns:
- `api_key = "..."`
- `API_KEY: ...`
- `token: sk-...`
- `secret: ...`

### REQ-MO-002: OAuth configuration validation
**EARS:** WHEN MCP сервер не использует OAuth 2.1 + PKCE для remote connections, THEN система ДОЛЖНА предупреждать.

Checks:
- OAuth 2.1 (не 2.0)
- PKCE presence
- Token refresh mechanism

### REQ-MO-003: Token exposure detection
**EARS:** WHEN токены находятся в logs/output, THEN система ДОЛЖНА флаговать token leakage.

### REQ-MO-004: Session management analysis
**EARS:** WHEN session lifetime > 24h без refresh, THEN система ДОЛЖНА предупреждать о stale sessions.

---

## Нефункциональные требования

### REQ-MO-NFR-001: Производительность
Анализ MCP config < 10ms.

---

## Критерии приёмки

- [ ] Patterns добавлены в mcp_security_monitor.py
- [ ] Unit tests покрывают все категории
- [ ] Документация обновлена
