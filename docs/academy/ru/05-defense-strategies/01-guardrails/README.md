# Guardrails (Primary)

> **Submodule 05.1b: Core Guardrail Implementation**

---

## �����

Guardrails are active controls that enforce security policies at runtime. This submodule covers implementation patterns for input, output, and system-level guardrails with practical code examples.

---

## Guardrail Types

| Type | Position | Purpose | Latency Impact |
|------|----------|---------|----------------|
| **Input** | Before LLM | Block malicious requests | Low |
| **Output** | After LLM | Block harmful responses | Medium |
| **System** | Always | Enforce invariants | Minimal |
| **Action** | Tool-level | Control agent actions | Low |

---

## Lessons

### 01. Input Guardrails
**�����:** 40 minutes | **���������:** �������

Filtering incoming requests:
- Content policy enforcement patterns
- Injection detection integration
- Topic restrictions implementation
- Rate limiting strategies

### 02. Output Guardrails
**�����:** 40 minutes | **���������:** �������

Filtering model responses:
- Harmful content blocking
- PII and credential redaction
- Policy compliance verification
- Response modification patterns

---

## Implementation Patterns

### Basic Guardrail
```python
from sentinel import Guard

guard = Guard(
    input_policy="strict",
    output_redaction=["pii", "credentials"],
    system_limits={"max_tokens": 4096, "timeout": 30}
)

@guard.protect
async def process_request(user_input: str) -> str:
    return await llm.generate(user_input)
```

---

## Guardrail Architecture

```
User Input
    │
    ▼
┌────────────────────┐
│  INPUT GUARDRAILS  │ ← Block/modify before LLM
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
│ OUTPUT GUARDRAILS  │ ← Block/modify after LLM
│  ├── Content check │
│  ├── PII redaction │
│  └── Policy verify │
└────────────────────┘
    │ (if safe)
    ▼
User Response
```

---

## ���������

| Previous | Current | Next |
|----------|---------|------|
| [Detection](../01-detection/) | **Guardrails** | [Response](../02-response/) |

---

*AI Security Academy | Core Guardrails*
