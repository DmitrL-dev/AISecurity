# Guardrails (Primary)

> **Submodule 05.1b: Core Guardrail Implementation**

---

## Overview

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
**Time:** 40 minutes | **Difficulty:** Intermediate

Filtering incoming requests:
- Content policy enforcement patterns
- Injection detection integration
- Topic restrictions implementation
- Rate limiting strategies

### 02. Output Guardrails
**Time:** 40 minutes | **Difficulty:** Intermediate

Filtering model responses:
- Harmful content blocking
- PII and credential redaction
- Policy compliance verification
- Response modification patterns

### 03. System Guardrails
**Time:** 35 minutes | **Difficulty:** Intermediate

Infrastructure-level controls:
- Token budget enforcement
- Timeout implementation patterns
- Resource quota management
- Circuit breaker design

### 04. Guardrail Composition
**Time:** 35 minutes | **Difficulty:** Advanced

Combining multiple guardrails:
- Layered guardrail architecture
- Performance optimization
- Conflict resolution
- Fallback strategies

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

### Custom Guardrail
```python
class CustomGuardrail:
    def __init__(self, policy: dict):
        self.policy = policy
    
    def check_input(self, text: str) -> bool:
        # Custom validation logic
        return not self._contains_forbidden(text)
    
    def check_output(self, text: str) -> str:
        # Custom redaction logic
        return self._redact_sensitive(text)
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

## Navigation

| Previous | Current | Next |
|----------|---------|------|
| [Detection](../01-detection/) | **Guardrails** | [Response](../02-response/) |

---

*AI Security Academy | Core Guardrails*
