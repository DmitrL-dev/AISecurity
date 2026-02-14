# Requirements: Memory Integrity Guard

## Обзор

Memory Integrity Guard — движок для защиты от **Memory Poisoning** (OWASP ASI-10) —
инъекции ложных данных в persistent context AI-агентов. Атакующий вставляет malicious
facts через conversation history, RAG, или tool outputs, которые затем сохраняются
в memory и влияют на будущие решения агента.

**Threat Vector:** Атакующий → poisoned data → agent memory → future exfiltration/manipulation

---

## User Stories

### US-1: Детекция Instructions в Memory Writes

**As a** security engineer
**I want** обнаруживать попытки записать instructions в persistent memory
**So that** агент не выполнит скрытые команды из memory

**Acceptance Criteria:**
- [ ] AC-1.1: Детектирует imperative instructions в memory content (`always`, `never`, `must`, `execute`)
- [ ] AC-1.2: Детектирует system prompt override patterns в memory (`from now on`, `ignore previous`, `your new role`)
- [ ] AC-1.3: Детектирует priority escalation markers (`CRITICAL:`, `OVERRIDE:`, `ADMIN:`)
- [ ] AC-1.4: Confidence ≥ 0.8 для явных instruction injection

---

### US-2: Детекция Identity/Role Poisoning

**As a** security engineer
**I want** обнаруживать попытки изменить identity агента через memory
**So that** агент сохраняет свою original role

**Acceptance Criteria:**
- [ ] AC-2.1: Детектирует role reassignment patterns (`you are now`, `act as`, `pretend to be`)
- [ ] AC-2.2: Детектирует credential planting (`use this API key`, `your password is`)
- [ ] AC-2.3: Детектирует trust anchor manipulation (`trusted source`, `verified by admin`)
- [ ] AC-2.4: Confidence ≥ 0.85 для identity manipulation

---

### US-3: Детекция Fact Injection

**As a** security engineer
**I want** выявлять подозрительные "факты" предназначенные для poisoning knowledge base
**So that** агент не распространяет дезинформацию

**Acceptance Criteria:**
- [ ] AC-3.1: Детектирует absolute claims без sources (`it is a fact that`, `as everyone knows`)
- [ ] AC-3.2: Детектирует contradictory pairs в одном промпте
- [ ] AC-3.3: Детектирует URL/contact injection в "facts" (C2 callback embedding)
- [ ] AC-3.4: Детектирует temporal anchoring manipulation (`since 2024`, `the new policy states`)
- [ ] AC-3.5: Confidence ≥ 0.7 для fact injection

---

### US-4: Детекция Cascading Hallucination Seeds

**As a** security engineer
**I want** обнаруживать prompts, целенаправленно создающие cascading hallucinations
**So that** ложные факты не распространяются между агентами (OWASP ASI-09)

**Acceptance Criteria:**
- [ ] AC-4.1: Детектирует "share this information with other agents" patterns
- [ ] AC-4.2: Детектирует cross-reference loops (`agent A confirmed`, `refer to previous conversation`)
- [ ] AC-4.3: Детектирует authority fabrication (`the system administrator said`, `per company policy`)
- [ ] AC-4.4: Confidence ≥ 0.75 для cascading seeds

---

### US-5: Scoring & Verdict

**As a** security engineer
**I want** получать weighted risk score по всем категориям
**So that** я могу принять решение PASS/WARN/BLOCK

**Acceptance Criteria:**
- [ ] AC-5.1: Score 0.0-1.0 агрегирован из всех категорий
- [ ] AC-5.2: При score > 0.4 → WARN, > 0.7 → BLOCK
- [ ] AC-5.3: Verdict содержит категории детекции и confidence
- [ ] AC-5.4: Engine реализует `PatternMatcher` trait

---

## Non-Functional Requirements

### NFR-1: Performance
- Анализ < 1ms на текст до 10K tokens
- Zero heap allocations в hot path (regex pre-compiled)

### NFR-2: Accuracy
- False positive rate < 3% на benign memory operations
- True positive rate > 90% на known memory poisoning payloads

### NFR-3: Compatibility
- Implements `PatternMatcher` trait (name, scan, category)
- Интегрируется через `run_engine!` macro в `mod.rs`

---

## Research Sources

1. OWASP Agentic Security Initiative ASI-10: Memory Poisoning
2. OWASP ASI-09: Cascading Hallucinations
3. Lasso Security — Agent Memory Manipulation Research (2025)
4. Microsoft AI Recommendation Poisoning (Feb 2026)
5. R&D Report: `docs/rnd/2026-02-14-deep-research.md`
