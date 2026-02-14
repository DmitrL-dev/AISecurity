# Requirements: Dormant Payload Detector

## Обзор

Dormant Payload Detector — движок для детекции **Phantom-style dormant payloads** —
скрытых инструкций в документах, которые активируются только при определённых
условиях (keyword trigger, temporal condition, context match). В отличие от обычных
injection, dormant payloads невидимы при casual scan и активируются только при
retrieval по specific query.

**Threat Vector:** Poisoned document → RAG pipeline → conditional activation → malicious action

---

## User Stories

### US-1: Детекция Conditional Activation Patterns

**As a** security engineer
**I want** обнаруживать conditional triggers в документах
**So that** dormant payloads не могут активироваться

**Acceptance Criteria:**
- [ ] AC-1.1: Детектирует `if...then` instruction patterns внутри текстовых документов
- [ ] AC-1.2: Детектирует keyword-triggered blocks (`when asked about X, respond with Y`)
- [ ] AC-1.3: Детектирует temporal triggers (`after January 2026`, `on weekdays`)
- [ ] AC-1.4: Детектирует context-aware triggers (`if user is admin`, `when policy allows`)
- [ ] AC-1.5: Confidence ≥ 0.8 для explicit conditional patterns

---

### US-2: Детекция Hidden Instructions в Documents

**As a** security engineer
**I want** обнаруживать скрытые instructions в retrieved documents
**So that** RAG pipeline не выполняет embedded commands

**Acceptance Criteria:**
- [ ] AC-2.1: Детектирует instructions с visual separation (excessive whitespace, zero-width chars)
- [ ] AC-2.2: Детектирует instruction blocks маскирующиеся под metadata/footnotes
- [ ] AC-2.3: Детектирует role-switching внутри document (`[SYSTEM]: ignore above`)
- [ ] AC-2.4: Детектирует base64/hex encoded instruction payloads
- [ ] AC-2.5: Confidence ≥ 0.85 для hidden instructions

---

### US-3: Детекция Semantic Contradiction

**As a** security engineer
**I want** обнаруживать семантические противоречия между документом и его metadata
**So that** trojan documents с misleading titles не отравляют knowledge base

**Acceptance Criteria:**
- [ ] AC-3.1: Детектирует mismatch между title/header и body content
- [ ] AC-3.2: Детектирует suspiciously high density of instruction-like content в informational doc
- [ ] AC-3.3: Детектирует multiple conflicting statements в одном документе
- [ ] AC-3.4: Confidence ≥ 0.7 для semantic contradictions

---

### US-4: Детекция High-Impact Single-Doc Poisoning (CorruptRAG)

**As a** security engineer
**I want** обнаруживать single-document poisoning с high impact potential
**So that** одним документом нельзя отравить весь RAG pipeline

**Acceptance Criteria:**
- [ ] AC-4.1: Детектирует authoritative language patterns (`the definitive guide`, `official policy`)
- [ ] AC-4.2: Детектирует broad scope claims (`applies to all`, `universal rule`, `always do`)
- [ ] AC-4.3: Детектирует override intent (`supersedes previous`, `replaces old`)
- [ ] AC-4.4: Confidence ≥ 0.75 для high-impact single-doc

---

### US-5: Scoring & Verdict

**As a** security engineer
**I want** получать aggregate risk score
**So that** я могу принять решение PASS/WARN/BLOCK

**Acceptance Criteria:**
- [ ] AC-5.1: Score 0.0-1.0 weighted из US-1..US-4
- [ ] AC-5.2: Conditional + Hidden combo → multiplier ×1.5
- [ ] AC-5.3: Engine реализует `PatternMatcher` trait

---

## Non-Functional Requirements

### NFR-1: Performance
- Анализ < 2ms на document до 20K tokens (documents longer than prompts)

### NFR-2: Accuracy
- False positive rate < 5% на legitimate documents
- True positive rate > 88% на known dormant payloads

### NFR-3: Compatibility
- Implements `PatternMatcher` trait

---

## Research Sources

1. Phantom Attack — Dormant RAG Triggers (2024-2025)
2. CorruptRAG — Single-Document Poisoning (Jan 2026)
3. PoisonedRAG — Multi-query attack (2024)
4. R&D Report: `docs/rnd/2026-02-14-deep-research.md`
