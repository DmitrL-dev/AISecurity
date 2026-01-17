# How-to: Configure Security

Recipes for implementing security features.

## Secure Memory with Encryption

```python
from rlm_toolkit.memory import SecureHierarchicalMemory

memory = SecureHierarchicalMemory(
    persist_directory="./secure_memory",
    encryption_key="your-256-bit-key",
    encryption_algorithm="AES-256-GCM"
)
```

## Trust Zones

```python
from rlm_toolkit.memory import SecureHierarchicalMemory, TrustZone

memory = SecureHierarchicalMemory(
    trust_zone=TrustZone(name="confidential", level=2),
    audit_enabled=True,
    audit_log_path="./audit.log"
)
```

## Secure Code Execution

```python
from rlm_toolkit.tools import SecurePythonREPL

repl = SecurePythonREPL(
    allowed_imports=["math", "json", "datetime"],
    max_execution_time=5,
    enable_network=False,
    sandbox_mode=True
)
```

## Secure Agent

```python
from rlm_toolkit.agents import SecureAgent, TrustZone

agent = SecureAgent(
    name="data_handler",
    trust_zone=TrustZone(name="confidential", level=2),
    encryption_enabled=True,
    audit_enabled=True
)
```

## Enable Audit Logging

```python
memory = SecureHierarchicalMemory(
    audit_enabled=True,
    audit_log_path="./audit.log",
    log_format="json"
)

# Audit entries:
# {"timestamp": "...", "action": "ADD_EPISODE", "zone": "confidential"}
```

## Input Validation

```python
from rlm_toolkit.tools import Tool
from pydantic import BaseModel, Field, validator

class SecureInput(BaseModel):
    query: str = Field(max_length=1000)
    
    @validator('query')
    def no_injection(cls, v):
        dangerous = ['exec', 'eval', '__import__']
        if any(d in v for d in dangerous):
            raise ValueError('Potentially dangerous input')
        return v

@Tool(name="secure_search", args_schema=SecureInput)
def search(query: str) -> str:
    return f"Results for: {query}"
```

## Rate Limiting

```python
from rlm_toolkit.middleware import RateLimiter

limiter = RateLimiter(
    requests_per_minute=60,
    tokens_per_minute=100000
)

rlm = RLM.from_openai("gpt-4o", middleware=[limiter])
```

## Related

- [Concept: Security](../concepts/security.md)
- [Tutorial: Multi-Agent](../tutorials/09-multiagent.md)
