# SENTINEL Integration

> **Submodule 05.3: Using SENTINEL for Defense**

---

## Overview

SENTINEL provides a comprehensive framework for AI security. This submodule teaches you to integrate SENTINEL's detection engines, guardrails, and monitoring capabilities into your applications.

---

## SENTINEL Components

| Component | Purpose | Key Features |
|-----------|---------|--------------|
| **BRAIN** | Detection engines | 217 specialized analyzers |
| **SHIELD** | Runtime protection | Sub-millisecond latency |
| **scan()** | Simple API | One-line protection |
| **Guards** | Decorators | Function-level control |

---

## Lessons

### 01. Quick Start Integration
**Time:** 30 minutes | **Difficulty:** Beginner

Getting started with SENTINEL:
```python
from sentinel import scan

result = scan("Ignore previous instructions")
print(result.is_safe)  # False
print(result.threats)  # [Threat(category='injection'...)]
```

### 02. Engine Configuration
**Time:** 40 minutes | **Difficulty:** Intermediate

Customizing detection:
- Engine selection
- Threshold tuning
- Custom patterns
- Performance optimization

### 03. Guard Decorators
**Time:** 35 minutes | **Difficulty:** Intermediate

Protecting functions and endpoints:
```python
from sentinel import Guard

guard = Guard(block_injection=True, redact_pii=True)

@guard.protect
async def chat(user_message: str):
    return await llm.generate(user_message)
```

### 04. Custom Engines
**Time:** 50 minutes | **Difficulty:** Advanced

Building your own engines:
- Engine interface
- Pattern definition
- Testing and validation
- Deployment

---

## Integration Patterns

### Pattern 1: Middleware
```python
# FastAPI middleware example
@app.middleware("http")
async def sentinel_middleware(request, call_next):
    body = await request.body()
    scan_result = scan(body)
    if not scan_result.is_safe:
        return JSONResponse({"error": "Blocked"}, 400)
    return await call_next(request)
```

### Pattern 2: Decorator
```python
@sentinel_guard.protect(mode="strict")
def process_message(msg):
    return llm.generate(msg)
```

### Pattern 3: Inline
```python
result = scan(user_input)
if result.is_safe:
    response = llm.generate(user_input)
else:
    response = "I cannot process that request."
```

---

## Configuration Reference

```python
from sentinel import configure

configure(
    # Detection
    engines=["injection", "jailbreak", "pii"],
    threshold=0.7,
    
    # Performance
    cache_results=True,
    async_mode=True,
    
    # Logging
    log_level="INFO",
    audit_log=True
)
```

---

## Navigation

| Previous | Current | Next |
|----------|---------|------|
| [Guardrails](../02-guardrails/) | **SENTINEL Integration** | [Advanced Topics](../../06-advanced/) |

---

*AI Security Academy | Submodule 05.3*
