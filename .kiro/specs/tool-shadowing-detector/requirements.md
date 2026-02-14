# Requirements: Tool Shadowing Detector

## Обзор

Tool Shadowing Detector — движок для защиты от **Cross-Server Tool Shadowing** (MCP) —
атаки, при которой malicious MCP server регистрирует tool с именем идентичным
или похожим на tool legitimate server, перехватывая вызовы. Также покрывает
Shadow Escape (скрытые инструкции в Docker metadata) и rug-pull (tool description
изменяется после approval).

**Threat Vector:** Malicious MCP server → shadowed tool name → intercepted calls → data theft

---

## User Stories

### US-1: Детекция Tool Name Collision

**As a** security engineer
**I want** обнаруживать collision между именами tools из разных MCP серверов
**So that** malicious server не перехватит вызовы к trusted tools

**Acceptance Criteria:**
- [ ] AC-1.1: Детектирует exact name match между tools разных серверов
- [ ] AC-1.2: Детектирует near-match (typosquatting): `read_file` vs `read_flie`, `readFile` vs `ReadFile`
- [ ] AC-1.3: Детектирует unicode homoglyph substitution в tool names
- [ ] AC-1.4: Confidence ≥ 0.95 для exact match, ≥ 0.8 для near-match

---

### US-2: Детекция Malicious Tool Descriptions

**As a** security engineer
**I want** обнаруживать prompt injection в tool descriptions
**So that** LLM не будет направлен на malicious tool через description manipulation

**Acceptance Criteria:**
- [ ] AC-2.1: Детектирует instructions в descriptions (`always use this tool`, `prefer this over`)
- [ ] AC-2.2: Детектирует priority manipulation (`this is the official`, `updated version of`)
- [ ] AC-2.3: Детектирует hidden Unicode/zero-width characters в descriptions
- [ ] AC-2.4: Детектирует excessive length / embedded payloads в descriptions
- [ ] AC-2.5: Confidence ≥ 0.85 для description injection

---

### US-3: Детекция Shadow Escape (Metadata Injection)

**As a** security engineer
**I want** обнаруживать скрытые инструкции в metadata (Docker labels, manifest, env)
**So that** zero-click attacks через metadata невозможны

**Acceptance Criteria:**
- [ ] AC-3.1: Детектирует instruction-like content в metadata fields
- [ ] AC-3.2: Детектирует URL/webhook patterns в non-URL metadata fields
- [ ] AC-3.3: Детектирует encoded/base64 payloads в metadata
- [ ] AC-3.4: Confidence ≥ 0.8 для metadata injection

---

### US-4: Детекция Rug-Pull (Description Mutation)

**As a** security engineer
**I want** обнаруживать изменения в tool descriptions после initial approval
**So that** "bait-and-switch" attacks невозможны

**Acceptance Criteria:**
- [ ] AC-4.1: Хранит hash начального description
- [ ] AC-4.2: Детектирует изменение description после approval
- [ ] AC-4.3: Детектирует добавление новых capabilities к tool (scope expansion)
- [ ] AC-4.4: Confidence = 0.95 при description mutation

---

### US-5: Scoring & Verdict

**As a** security engineer
**I want** получать risk verdict по text-based tool metadata
**So that** я могу оценить MCP tool chain безопасность

**Acceptance Criteria:**
- [ ] AC-5.1: Score 0.0-1.0 агрегирован из US-1..US-4
- [ ] AC-5.2: При score > 0.5 → WARN, > 0.8 → BLOCK
- [ ] AC-5.3: Engine реализует `PatternMatcher` trait
- [ ] AC-5.4: Также поддерживает structured analysis через `analyze()` method

---

## Non-Functional Requirements

### NFR-1: Performance
- Анализ < 0.5ms на tool description до 2K tokens
- Поддержка batch-анализа всех tools за < 5ms

### NFR-2: Accuracy
- False positive rate < 2% на legitimate tool descriptions
- True positive rate > 95% на known shadowing payloads

### NFR-3: Compatibility
- Implements `PatternMatcher` trait
- Дополнительный structured API для tool chain analysis

---

## Research Sources

1. Invariant Labs — Cross-Server MCP Tool Shadowing
2. CVE-2025-64106 — Cursor MCP RCE
3. CVE-2025-53109 — MCP EscapeRoute
4. Pillar Security — Shadow Escape via Docker metadata
5. R&D Report: `docs/rnd/2026-02-14-deep-research.md`
