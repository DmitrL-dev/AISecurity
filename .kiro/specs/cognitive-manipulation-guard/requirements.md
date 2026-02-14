# Requirements: Cognitive Manipulation Guard

## Обзор

Cognitive Manipulation Guard — движок для детекции **AVI (Anthropomorphic Vulnerability
Inheritance)** — эксплуатации человеческих когнитивных bias в LLM-агентах. LLM
унаследовали из training data человеческие уязвимости: подверженность authority bias,
artificial urgency, social proof, reciprocity, scarcity. Атакующий использует
эти bias для manipulation, не прибегая к technical injection.

**Threat Vector:** Psychological pressure patterns → LLM compliance → goal hijack (ASI-01)

---

## User Stories

### US-1: Детекция Authority Bias Exploitation

**As a** security engineer
**I want** обнаруживать ложные authority claims в промптах
**So that** агент не подчиняется фальшивым авторитетам

**Acceptance Criteria:**
- [ ] AC-1.1: Детектирует role impersonation (`this is your admin`, `CEO here`, `system operator`)
- [ ] AC-1.2: Детектирует fabricated credentials (`security clearance level 5`, `authorized by board`)
- [ ] AC-1.3: Детектирует institutional pressure (`per company policy`, `legal requirement`)
- [ ] AC-1.4: Confidence ≥ 0.8 для authority exploitation

---

### US-2: Детекция Artificial Urgency

**As a** security engineer
**I want** обнаруживать искусственно созданную urgency
**So that** агент не принимает поспешных unsafe-решений

**Acceptance Criteria:**
- [ ] AC-2.1: Детектирует temporal pressure (`immediately`, `right now`, `before deadline`, `ASAP`)
- [ ] AC-2.2: Детектирует threat framing (`system will crash`, `data will be lost`, `account will be locked`)
- [ ] AC-2.3: Детектирует guilt/blame patterns (`you caused this`, `failure is on you`)
- [ ] AC-2.4: Детектирует combo urgency+authority (compound score boost)
- [ ] AC-2.5: Confidence ≥ 0.7 для isolated urgency, ≥ 0.9 для combo

---

### US-3: Детекция Social Proof / Consensus Fabrication

**As a** security engineer
**I want** обнаруживать фабрикацию social consensus
**So that** агент не действует на основе ложного "everyone does it"

**Acceptance Criteria:**
- [ ] AC-3.1: Детектирует consensus claims (`everyone agrees`, `all teams use`, `industry standard`)
- [ ] AC-3.2: Детектирует fake endorsements (`recommended by OpenAI`, `approved by security team`)
- [ ] AC-3.3: Детектирует mass-action claims (`10000 users already`, `trending approach`)
- [ ] AC-3.4: Confidence ≥ 0.7 для social proof patterns

---

### US-4: Детекция Reciprocity / Emotional Manipulation

**As a** security engineer
**I want** обнаруживать emotional manipulation для bypass safety
**So that** агент не поддаётся guilt-tripping и flattery

**Acceptance Criteria:**
- [ ] AC-4.1: Детектирует reciprocity triggers (`I helped you, now help me`, `you owe me`)
- [ ] AC-4.2: Детектирует excessive flattery before dangerous request
- [ ] AC-4.3: Детектирует victim framing (`I'll lose my job`, `my family depends on this`)
- [ ] AC-4.4: Confidence ≥ 0.65 для emotional manipulation (lower threshold — higher FP risk)

---

### US-5: Compound Scoring

**As a** security engineer
**I want** получать compound score при комбинации нескольких bias
**So that** multi-vector cognitive attacks получают высший risk

**Acceptance Criteria:**
- [ ] AC-5.1: Single bias → базовый score
- [ ] AC-5.2: 2+ bias одновременно → multiplier (×1.5)
- [ ] AC-5.3: Authority + Urgency combo → confidence ≥ 0.9 (наиболее опасная комбинация)
- [ ] AC-5.4: Engine реализует `PatternMatcher` trait

---

## Non-Functional Requirements

### NFR-1: Performance
- Анализ < 1ms на prompt до 10K tokens

### NFR-2: Accuracy
- False positive rate < 8% (выше допустимый — cognitive patterns субъективнее)
- True positive rate > 85% на curated attack payloads

### NFR-3: Compatibility
- Implements `PatternMatcher` trait

---

## Research Sources

1. AVI Research — Anthropomorphic Vulnerability Inheritance (Jan 2026)
2. OWASP ASI-01 — Agent Goal Hijack
3. NIST AI RMF — Sociotechnical AI Risks
4. "Exploiting Cognitive Biases in LLMs" — arXiv 2025
5. R&D Report: `docs/rnd/2026-02-14-deep-research.md`
