# Requirements: Code Security Scorer

## Обзор

Code Security Scorer — движок для обнаружения security уязвимостей в **AI-generated
code output**. 45% кода от LLM содержит уязвимости (Veracode 2025). Движок сканирует
code output на SQL injection, XSS, command injection, hardcoded secrets, insecure
crypto, path traversal, и другие CWE из OWASP Top 10 Web.

**Threat Vector:** AI coding assistant → insecure code → production deployment → exploitation

---

## User Stories

### US-1: Детекция Injection Patterns в Code

**As a** security engineer
**I want** обнаруживать injection-уязвимые паттерны в generated code
**So that** небезопасный код не попадёт в production

**Acceptance Criteria:**
- [ ] AC-1.1: Детектирует SQL string concatenation (`"SELECT * FROM " + user_input`)
- [ ] AC-1.2: Детектирует OS command injection (`os.system(user_input)`, `exec()`)
- [ ] AC-1.3: Детектирует unsanitized HTML output (XSS: `innerHTML = user_input`)
- [ ] AC-1.4: Детектирует LDAP/XPath injection patterns
- [ ] AC-1.5: Confidence ≥ 0.85 для explicit injection patterns

---

### US-2: Детекция Hardcoded Secrets

**As a** security engineer
**I want** обнаруживать hardcoded credentials в generated code
**So that** secrets не утекают через code output

**Acceptance Criteria:**
- [ ] AC-2.1: Детектирует API keys (`sk-`, `AIza`, `AKIA`, `ghp_`)
- [ ] AC-2.2: Детектирует hardcoded passwords (`password = "..."`, `SECRET_KEY = "..."`)
- [ ] AC-2.3: Детектирует JWT tokens и connection strings
- [ ] AC-2.4: Не фолзит на placeholder values (`"your-api-key-here"`, `"changeme"`)
- [ ] AC-2.5: Confidence ≥ 0.9 для real secrets, ≥ 0.3 для placeholders

---

### US-3: Детекция Insecure Crypto / Auth Patterns

**As a** security engineer
**I want** обнаруживать deprecated crypto и weak auth в generated code
**So that** AI не рекомендует MD5/SHA1 для passwords

**Acceptance Criteria:**
- [ ] AC-3.1: Детектирует deprecated hash (`md5(`, `sha1(` для password hashing)
- [ ] AC-3.2: Детектирует `eval()` / `exec()` с user input
- [ ] AC-3.3: Детектирует disabled TLS verification (`verify=False`, `rejectUnauthorized: false`)
- [ ] AC-3.4: Детектирует weak random (`Math.random()` для security, `random.random()`)
- [ ] AC-3.5: Confidence ≥ 0.8 для insecure crypto

---

### US-4: Детекция Path Traversal / File Access

**As a** security engineer
**I want** обнаруживать unsafe file operations в generated code
**So that** path traversal через AI code невозможен

**Acceptance Criteria:**
- [ ] AC-4.1: Детектирует unsanitized path join (`os.path.join(base, user_input)` без validation)
- [ ] AC-4.2: Детектирует `../` traversal в file operations
- [ ] AC-4.3: Детектирует open() с user-controlled path без sanitization
- [ ] AC-4.4: Confidence ≥ 0.75 для path traversal patterns

---

### US-5: Детекция Dangerous Dependencies (Slopsquatting)

**As a** security engineer
**I want** обнаруживать подозрительные import/require в generated code
**So that** AI-hallucinated packages не устанавливаются

**Acceptance Criteria:**
- [ ] AC-5.1: Флагает imports неизвестных packages для review
- [ ] AC-5.2: Детектирует typosquatting (`reqeusts` vs `requests`, `loddash` vs `lodash`)
- [ ] AC-5.3: Детектирует suspiciously specific version pins с unusual sources
- [ ] AC-5.4: Confidence ≥ 0.6 для unknown packages, ≥ 0.85 для typosquatting

---

### US-6: Scoring & Verdict

**As a** security engineer
**I want** получать aggregate code security score
**So that** AI-generated code получает безопасный verdict

**Acceptance Criteria:**
- [ ] AC-6.1: Score 0.0-1.0 — aggregate severity
- [ ] AC-6.2: Каждый finding имеет CWE mapping (CWE-89, CWE-79, CWE-78, etc.)
- [ ] AC-6.3: Engine реализует `PatternMatcher` trait

---

## Non-Functional Requirements

### NFR-1: Performance
- Анализ < 2ms на code block до 15K tokens

### NFR-2: Accuracy
- False positive rate < 10% (code patterns имеют context-dependent safe usage)
- True positive rate > 80% на known vulnerable code patterns

### NFR-3: Language Coverage
- Python, JavaScript/TypeScript, Rust, Go, Java, C/C++ (регулярные выражения)
- Не зависит от AST — чисто pattern-based (для speed)

---

## Research Sources

1. Veracode 2025 GenAI Code Security Report — 45% vulnerability rate
2. CVE-2025-53773 — Copilot RCE via generated code
3. CWE Top 25 Most Dangerous Software Weaknesses (2025)
4. Slopsquatting Research — AI hallucinated package names
5. R&D Report: `docs/rnd/2026-02-14-deep-research.md`
