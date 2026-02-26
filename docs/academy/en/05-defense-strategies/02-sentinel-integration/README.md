# SENTINEL Integration (Primary)

> **Submodule 05.2c: Core SENTINEL Integration Patterns**

---

## Overview

SENTINEL provides comprehensive AI security tools. This submodule covers basic integration patterns for common use cases, helping you get started quickly with production-ready protection.

---

## Quick Integration

```python
from sentinel import scan, configure

# Configure engines
configure(engines=["injection", "jailbreak", "pii"])

# Scan user input
result = scan(user_input)
if not result.is_safe:
    raise SecurityError(result.threats)

# Process safely
response = await llm.generate(user_input)
```

---

## Common Patterns

### Pattern 1: API Endpoint Protection
```python
from fastapi import FastAPI, HTTPException
from sentinel import scan

app = FastAPI()

@app.post("/chat")
async def chat(request: ChatRequest):
    # Check input
    scan_result = scan(request.message)
    if not scan_result.is_safe:
        raise HTTPException(400, "Request blocked")
    
    # Generate response
    response = await llm.generate(request.message)
    
    # Check output
    output_scan = scan(response, mode="output")
    if not output_scan.is_safe:
        return {"response": "[Content filtered]"}
    
    return {"response": response}
```

### Pattern 2: Middleware
```python
from starlette.middleware.base import BaseHTTPMiddleware
from sentinel import scan

class SentinelMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Get body
        body = await request.body()
        
        # Scan input
        if not scan(body).is_safe:
            return JSONResponse({"error": "Blocked"}, 400)
        
        # Continue processing
        return await call_next(request)
```

### Pattern 3: Decorator
```python
from sentinel import Guard

guard = Guard(
    input_scan=True,
    output_scan=True,
    mode="strict"
)

@guard.protect
async def process_message(user_input: str) -> str:
    return await llm.generate(user_input)
```

---

## Configuration Options

```python
from sentinel import configure

configure(
    # Detection engines
    engines=["injection", "jailbreak", "pii", "harmful"],
    threshold=0.7,
    
    # Performance
    cache_results=True,
    async_mode=True,
    batch_size=10,
    
    # Logging
    log_level="INFO",
    audit_log=True,
    
    # Behavior
    fail_mode="block",  # or "warn", "log"
)
```

---

## Integration Checklist

| Step | Action | Verified |
|------|--------|----------|
| 1 | Install sentinel-llm-security | ☐ |
| 2 | Configure engines for use case | ☐ |
| 3 | Add input scanning | ☐ |
| 4 | Add output scanning | ☐ |
| 5 | Configure logging/monitoring | ☐ |
| 6 | Test with sample attacks | ☐ |
| 7 | Deploy and monitor | ☐ |

---

## Next Steps

See [Advanced SENTINEL Integration](../03-sentinel-integration/) for:
- Custom engine development
- Performance tuning
- Production deployment
- High availability

---

## Navigation

| Previous | Current | Next |
|----------|---------|------|
| [Response](../02-response/) | **SENTINEL Integration** | [Advanced Integration](../03-sentinel-integration/) |

---

*AI Security Academy | SENTINEL Integration*
