# Guardrails

> **Submodule 05.2: Preventing Harmful Outcomes**

---

## Overview

Guardrails are active controls that prevent harmful inputs from reaching the model and harmful outputs from reaching users. They complement detection by adding enforcement.

---

## Guardrail Types

| Type | Position | Purpose |
|------|----------|---------|
| **Input** | Pre-LLM | Block harmful requests |
| **Output** | Post-LLM | Block harmful responses |
| **System** | Always | Enforce invariants |
| **Action** | Tool-level | Control agent actions |

---

## Lessons

### 01. Input Guardrails
**Time:** 40 minutes | **Difficulty:** Intermediate

Filtering incoming requests:
- Content policy enforcement
- Topic restrictions
- Rate limiting
- User reputation scoring

### 02. Output Guardrails
**Time:** 40 minutes | **Difficulty:** Intermediate

Filtering model responses:
- Harmful content detection
- PII/credential redaction
- Policy compliance
- Response modification

### 03. System Guardrails
**Time:** 35 minutes | **Difficulty:** Intermediate

Infrastructure-level controls:
- Token budget limits
- Timeout enforcement
- Resource quotas
- Circuit breakers

### 04. Action Guardrails
**Time:** 45 minutes | **Difficulty:** Advanced

Controlling agent actions:
- Tool allowlists/denylists
- Parameter constraints
- Confirmation requirements
- Rollback capability

---

## Guardrail Architecture

```
User Input
    │
    ▼
┌────────────────────┐
│  INPUT GUARDRAILS  │
│  ├── Policy check  │
│  ├── Injection scan│
│  └── Rate limit    │
└────────────────────┘
    │ (if allowed)
    ▼
┌────────────────────┐
│       LLM          │
└────────────────────┘
    │
    ▼
┌────────────────────┐
│ OUTPUT GUARDRAILS  │
│  ├── Content check │
│  ├── PII redaction │
│  └── Policy verify │
└────────────────────┘
    │ (if safe)
    ▼
User Response
```

---

## Implementation Patterns

| Pattern | Description | Use Case |
|---------|-------------|----------|
| **Allow list** | Only permit specified | Highly restricted environments |
| **Deny list** | Block known bad | General protection |
| **Threshold** | Allow if confidence low | Balanced approach |
| **Human-in-loop** | Flag for review | Uncertain cases |

---

## Key Metrics

- **Block rate** - % of requests/responses blocked
- **False positive rate** - % of legitimate content blocked
- **Latency impact** - Time added by guardrails
- **Coverage** - % of threat types addressed

---

## Navigation

| Previous | Current | Next |
|----------|---------|------|
| [Detection](../01-detection/) | **Guardrails** | [SENTINEL Integration](../03-sentinel-integration/) |

---

*AI Security Academy | Submodule 05.2*
