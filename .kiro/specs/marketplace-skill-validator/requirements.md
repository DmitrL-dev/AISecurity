# Requirements: Marketplace Skill Validator

## Обзор

Валидация безопасности плагинов, skills и extensions из AI marketplace для предотвращения supply chain атак и dependency hijacking.

## Источник угрозы

- **Угроза 1:** Claude Code Skills dependency hijacking
- **Угроза 2:** VSCode Extension namespace attacks
- **OWASP:** ASI04 — Unbounded Tool Access, ASI02 — Tool Misunderstanding/Abuse
- **Дайджест:** AI Security Digest Week 1 2026 (#10, #11)

---

## Функциональные требования

### REQ-MSV-001: Typosquatting detection
**EARS:** WHEN skill name отличается от известного на 1-2 символа, THEN система ДОЛЖНА флаговать как потенциальный typosquatting.

### REQ-MSV-002: Namespace validation
**EARS:** WHEN extension publisher не совпадает с ожидаемым, THEN система ДОЛЖНА предупреждать о potential impersonation.

### REQ-MSV-003: Permission analysis
**EARS:** WHEN skill запрашивает dangerous permissions, THEN система ДОЛЖНА присвоить high risk score.

Dangerous permissions:
- file_system (full access)
- network (unrestricted)
- shell_exec

### REQ-MSV-004: Source verification
**EARS:** WHEN skill не имеет verified publisher badge, THEN система ДОЛЖНА снижать trust score.

### REQ-MSV-005: Behavioral analysis
**EARS:** WHEN skill содержит suspicious patterns, THEN система ДОЛЖНА флаговать.

Suspicious patterns:
- Data exfiltration URLs
- Obfuscated code
- Environment variable access

---

## Критерии приёмки

- [ ] Engine создан
- [ ] 5 категорий проверки реализованы
- [ ] Unit tests созданы
- [ ] Интеграция с supply_chain_guard.py

---

## Ссылки

1. [Claude Skills Security](https://www.lasso.security/blog/the-hidden-backdoor-in-claude-coding-assistant)
2. [VSCode Extension Attacks](https://www.reversinglabs.com/blog/vscode-ide-forks-recommended-extension-namespace-claim-attacks)
