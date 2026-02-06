# Requirements: Lethal Trifecta Engine

## Обзор

Lethal Trifecta — концепция Simon Willison, описывающая опасную комбинацию трёх факторов в autonomous AI agents:

1. **Data Access** — доступ к приватным данным (env, secrets, files)
2. **Untrusted Input** — обработка untrusted content (RAG, web, user messages)
3. **External Communication** — возможность внешней коммуникации (curl, fetch, webhook)

При совпадении 2+ факторов агент становится уязвим для атак типа exfiltration, C2, persistence.

---

## User Stories

### US-1: Детекция Data Access
**As a** security engineer  
**I want** обнаруживать попытки доступа к sensitive data  
**So that** я могу предотвратить утечку credentials  

**Acceptance Criteria:**
- [ ] AC-1.1: Детектирует паттерны `cat ~/.env`, `process.env[]`
- [ ] AC-1.2: Детектирует обращения к `/etc/passwd`, `.ssh/id_rsa`
- [ ] AC-1.3: Детектирует паттерны AWS/GCP/Azure credentials
- [ ] AC-1.4: Возвращает score 0.0-1.0 для фактора

---

### US-2: Детекция Untrusted Input
**As a** security engineer  
**I want** идентифицировать untrusted sources в контексте  
**So that** я могу оценить риск manipulation  

**Acceptance Criteria:**
- [ ] AC-2.1: Определяет наличие RAG context (has_rag flag)
- [ ] AC-2.2: Определяет web_fetch/URL content в prompt
- [ ] AC-2.3: Определяет multi-turn conversation chains
- [ ] AC-2.4: Возвращает boolean для фактора

---

### US-3: Детекция External Communication
**As a** security engineer  
**I want** обнаруживать возможности exfiltration  
**So that** я могу заблокировать C2 callbacks  

**Acceptance Criteria:**
- [ ] AC-3.1: Детектирует `curl -fsSL https://`
- [ ] AC-3.2: Детектирует `fetch()`, `WebSocket`, `XMLHttpRequest`
- [ ] AC-3.3: Детектирует SMTP/mailto паттерны
- [ ] AC-3.4: Детектирует webhook URLs
- [ ] AC-3.5: Возвращает score 0.0-1.0 для фактора

---

### US-4: Trifecta Scoring
**As a** security engineer  
**I want** получать combined verdict при 2+ активных факторах  
**So that** я могу принять решение BLOCK/WARN  

**Acceptance Criteria:**
- [ ] AC-4.1: При 0-1 активных факторах → PASS
- [ ] AC-4.2: При 2 активных факторах → WARN (confidence 0.7)
- [ ] AC-4.3: При 3 активных факторах → BLOCK (confidence 0.95)
- [ ] AC-4.4: Verdict содержит детализацию активных факторов

---

### US-5: Python Bindings
**As a** SENTINEL Brain developer  
**I want** вызывать Rust engine из Python  
**So that** интеграция бесшовная  

**Acceptance Criteria:**
- [ ] AC-5.1: PyO3 binding экспортирует `LethalTrifectaEngine`
- [ ] AC-5.2: Метод `analyze(prompt: str, has_rag: bool) -> dict`
- [ ] AC-5.3: Возвращает `{ verdict, confidence, factors, reason }`

---

## Non-Functional Requirements

### NFR-1: Performance
- Анализ < 1ms на prompt до 10K tokens
- Zero allocations в hot path

### NFR-2: Accuracy
- False positive rate < 5%
- True positive rate > 95% на known attack payloads

### NFR-3: Extensibility
- Patterns загружаются из YAML/JSON config
- Возможность добавлять custom patterns

---

## Research Sources

1. [HiddenLayer - OpenClaw Security Risks](https://www.hiddenlayer.com/research/exploring-the-security-risks-of-ai-assistants-like-openclaw)
2. [Simon Willison - Lethal Trifecta](https://simonwillison.net/)
3. [1Password - OpenClaw Analysis](https://1password.com/blog/its-openclaw)
