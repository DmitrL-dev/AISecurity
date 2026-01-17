# Security Concept

RLM-Toolkit includes SENTINEL-grade security features for enterprise AI applications.

## Security Features

### Trust Zones
Memory and agent isolation levels:

| Zone | Level | Use Case |
|------|-------|----------|
| `public` | 0 | User-facing content |
| `internal` | 1 | Business logic |
| `confidential` | 2 | Personal data |
| `secret` | 3 | Highly sensitive |

```python
from rlm_toolkit.memory import SecureHierarchicalMemory

memory = SecureHierarchicalMemory(
    trust_zone="confidential",
    encryption_enabled=True
)
```

### Secure Code Execution
CIRCLE-compliant sandbox:

```python
from rlm_toolkit.tools import SecurePythonREPL

repl = SecurePythonREPL(
    allowed_imports=["math", "json"],
    max_execution_time=5,
    enable_network=False
)
```

### Encryption
AES-256-GCM for data at rest:

```python
memory = SecureHierarchicalMemory(
    encryption_key="your-256-bit-key",
    encryption_algorithm="AES-256-GCM"
)
```

### Audit Logging
Full operation history:

```python
memory = SecureHierarchicalMemory(
    audit_enabled=True,
    audit_log_path="./audit.log"
)
```

## Agent Security

Secure multi-agent communication:

```python
from rlm_toolkit.agents import SecureAgent, TrustZone

agent = SecureAgent(
    name="data_handler",
    trust_zone=TrustZone(name="confidential", level=2),
    encryption_enabled=True
)
```

## Related

- [Tutorial: Multi-Agent](../tutorials/09-multiagent.md)
- [Tutorial: H-MEM](../tutorials/07-hmem.md)
