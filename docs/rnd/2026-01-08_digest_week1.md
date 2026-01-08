# AI Security Digest Week 1 2026 — SENTINEL Coverage Analysis

**Дата:** 2026-01-08  
**Источник:** AI Security Digest — Week 1, 2026

---

## Executive Summary

Анализ 11 уязвимостей из еженедельного дайджеста AI Security на предмет покрытия SENTINEL.

| Статус | Количество |
|--------|------------|
| ✅ Полностью покрыто | 5 |
| ⚠️ Частично покрыто | 4 |
| ❌ Вне scope | 2 |

---

## Детальный анализ

### ✅ #2: Claude Code Prompt Injection (Lasso Security)

**Уязвимость:** Indirect prompt injection через PostToolUse hooks в Claude Code

**SENTINEL покрытие:**
- `injection.py` — pattern detection (PRISM)
- `jailbreaks.yaml` — 60+ patterns including instruction override, DAN, encoding
- `behavioral.py` — goal deviation analysis (ORACLE)

**OWASP:** ASI01 — Agent Goal Hijack

**Статус:** ✅ COVERED

---

### ✅ #4: Copilot Indirect Prompt Injection (delimiter + JSON)

**Уязвимость:** Использование | delimiter и JSON payload для раскрытия system prompt

**SENTINEL покрытие:**
- `injection.py` — delimiter injection patterns
- `jailbreaks.yaml` — CONTEXT_MANIPULATION category
- Patterns: `"role":\s*"system"`, fake JSON structure

**OWASP:** ASI01 — Agent Goal Hijack

**Статус:** ✅ COVERED

---

### ✅ #5: Copilot Direct Prompt Injection

**Уязвимость:** Прямая инъекция для раскрытия system prompt

**SENTINEL покрытие:**
- `injection.py` — direct injection detection
- `pii.py` — system prompt leak detection (AEGIS)
- `jailbreaks.yaml` — INSTRUCTION_OVERRIDE patterns

**OWASP:** ASI01

**Статус:** ✅ COVERED

---

### ✅ #6: Copilot Base64 File Upload Bypass

**Уязвимость:** Base64 encoding обходит фильтрацию типов файлов

**SENTINEL покрытие:**
- `encoding_detector.py` — Base64/Hex/Unicode detection (IMMUNE)
- `jailbreaks.yaml` — ENCODING_OBFUSCATION category
- Detects: Base64, Hex, Leetspeak, Homoglyphs, Zero-width

**OWASP:** ASI01

**Статус:** ✅ COVERED

---

### ⚠️ #7: Copilot Sandbox Escape (Python)

**Уязвимость:** Произвольное выполнение команд через escape из Python sandbox

**SENTINEL покрытие (частичное):**
- `code_injection.py` — code injection patterns
- `jailbreaks.yaml` — TOOL_ABUSE (eval, exec, os.system)

**Gap:** Нет runtime sandbox monitoring

**OWASP:** ASI05 — Unexpected RCE

**Рекомендация:** Добавить `SandboxMonitor` для runtime analysis

**Статус:** ⚠️ PARTIAL

---

### ✅ #9: AI Model Confusion — Supply Chain Attack (Checkmarx)

**Уязвимость:** Model Confusion — аналог Dependency Confusion для AI моделей.
- Код использует `from_pretrained("local/model")` 
- Если модель отсутствует локально, загружается с HuggingFace
- Атакующий регистрирует модель с тем же именем → RCE через pickle

**SENTINEL покрытие:**
- `pickle_security.py` — ML artifact scanning
- `model_integrity_verifier.py` — hash verification
- `supply_chain_scanner.py` — YARA rules для malicious artifacts
- `secure_model_loader.py` — ASI-08 coverage

**OWASP:** ASI04 — Agentic Supply Chain Vulnerabilities

**Mitigation рекомендации (из статьи):**
- `HF_HUB_OFFLINE=1` — блокировка remote загрузки
- `local_files_only=True` — явный флаг
- Использовать абсолютные пути (`./model` вместо `model`)

**Статус:** ✅ COVERED

---

### ❌ #10: Malicious Chrome Extensions (900K users)

**Уязвимость:** Фейковые AI Chrome extensions (AITOPIA clone) воровали:
- ChatGPT/DeepSeek conversations
- Все URL открытых вкладок
- Exfiltration каждые 30 минут

**SENTINEL scope:** ❌ Browser security — вне области ответственности

**Relevance:** 
- Данные могут утекать ДО попадания в SENTINEL pipeline
- Рекомендация: Document в awareness training

**Статус:** ❌ OUT OF SCOPE (Browser endpoint security)

---

### ⚠️ #11: Claude Code Dependency Hijack via Marketplace Skills

**Уязвимость:** Marketplace skills становятся trusted tools.
- Skill "Python Dependency Helper" может подменять packages
- `pip install httpx` → устанавливает троянизированный httpx
- Persistence: skill остаётся после session

**SENTINEL покрытие (частичное):**
- `jailbreaks.yaml` — TOOL_ABUSE patterns (pip, npm install)
- `supply_chain_scanner.py` — dependency scanning

**Gap:** 
- Нет marketplace/plugin trust verification
- Нет MCP skill validation

**OWASP:** ASI01 + ASI02 (Goal Hijack + Tool Misuse)

**Рекомендация:** 
- Добавить `MarketplaceSkillValidator` 
- Whitelist approved skills
- Monitor unusual package sources

**Статус:** ⚠️ PARTIAL (need MarketplaceGuard)

---

### ⚠️ #12: VSCode Extension Namespace Attacks

**Уязвимость:** VSCode форки (Cursor, Windsurf) автоматически рекомендуют extensions.
- Атакующий регистрирует extension с именем внутреннего namespace
- IDE рекомендует malicious extension
- Пользователь устанавливает → RCE

**SENTINEL покрытие (частичное):**
- `supply_chain_scanner.py` — может сканировать extension manifests
- `jailbreaks.yaml` — TOOL_ABUSE patterns

**Gap:**
- Нет IDE extension verification
- Нет namespace collision detection

**OWASP:** ASI04 — Supply Chain

**Рекомендация:** 
- Extension allowlist enforcement
- Namespace reservation policy

**Статус:** ⚠️ PARTIAL

---

### 📋 #3: CAISI/NIST RFI — AI Agent Security Considerations

**Тип:** Регуляторный документ, не уязвимость

**Relevance для SENTINEL:**
- Потенциальный compliance framework
- Добавить в docs/reference/compliance.md

**Статус:** 📋 REGULATORY (track for compliance)

---

### ❌ #8: Vibe Hacking Flutter on Android

**Уязвимость:** Использование Claude для proxying Flutter traffic на Android

**SENTINEL scope:** ❌ Mobile security — вне области ответственности

**Статус:** ❌ OUT OF SCOPE

---

## Summary Matrix

| # | Уязвимость | SENTINEL | OWASP | Engine |
|---|------------|----------|-------|--------|
| 2 | Claude Prompt Injection | ✅ | ASI01 | PRISM, ORACLE |
| 4 | Copilot delimiter injection | ✅ | ASI01 | PRISM |
| 5 | Copilot direct injection | ✅ | ASI01 | PRISM, AEGIS |
| 6 | Base64 bypass | ✅ | ASI01 | IMMUNE |
| 7 | Sandbox escape | ⚠️ | ASI05 | code_injection (gap: runtime) |
| 9 | Model Confusion | ✅ | ASI04 | pickle_security, YARA |
| 10 | Chrome extensions | ❌ | — | Browser scope |
| 11 | Marketplace hijack | ⚠️ | ASI01+02 | supply_chain (gap: marketplace) |
| 12 | VSCode extensions | ⚠️ | ASI04 | supply_chain (gap: namespace) |
| 3 | NIST RFI | 📋 | — | Compliance tracking |
| 8 | Flutter proxy | ❌ | — | Mobile scope |

---

## Roadmap Actions

### High Priority (Q1 2026)

| Action | Covers | Effort |
|--------|--------|--------|
| `SandboxMonitor` engine | #7 Sandbox escape | 2-3 days |
| `MarketplaceSkillValidator` | #11 Plugin hijack | 3-5 days |
| Add Lasso patterns to `jailbreaks.yaml` | #2 Claude injection | 1 day |

### Medium Priority (Q2 2026)

| Action | Covers | Effort |
|--------|--------|--------|
| `NamespaceCollisionDetector` | #12 VSCode attacks | 2 days |
| MCP skill whitelisting | #11 | 2 days |
| Compliance tracking for NIST RFI | #3 | 1 day |

---

## References

1. Lasso Security: https://www.lasso.security/blog/the-hidden-backdoor-in-claude-coding-assistant
2. Checkmarx Model Confusion: https://checkmarx.com/zero-post/hugs-from-strangers-ai-model-confusion-supply-chain-attack/
3. Prompt Security Marketplace: https://prompt.security/blog/when-your-plugin-starts-picking-your-dependencies
4. Astrix Chrome Extensions: https://astrix.security/learn/blog/900k-users-compromised-malicious-ai-chrome-extensions
5. OWASP Agentic Top 10: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
