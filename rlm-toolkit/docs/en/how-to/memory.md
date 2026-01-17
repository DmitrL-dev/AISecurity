# How-to: Configure Memory

Recipes for configuring memory systems in RLM-Toolkit.

## Basic Buffer Memory

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import BufferMemory

memory = BufferMemory(max_messages=100)
rlm = RLM.from_openai("gpt-4o", memory=memory)

response = rlm.run("Hello, I'm Alex")
response = rlm.run("What's my name?")  # "Your name is Alex"
```

## Token-Limited Memory

```python
from rlm_toolkit.memory import TokenBufferMemory

memory = TokenBufferMemory(
    max_tokens=4000,
    model="gpt-4o"
)
```

## Summary Memory

```python
from rlm_toolkit.memory import SummaryMemory

memory = SummaryMemory(
    summarizer=RLM.from_openai("gpt-4o-mini"),
    max_tokens=2000
)
```

## Persistent Memory (H-MEM)

```python
from rlm_toolkit.memory import HierarchicalMemory, HMEMConfig

config = HMEMConfig(
    episode_limit=100,
    consolidation_enabled=True,
    consolidation_threshold=25
)

memory = HierarchicalMemory(
    config=config,
    persist_directory="./memory"
)
```

## Secure Memory with Encryption

```python
from rlm_toolkit.memory import SecureHierarchicalMemory

memory = SecureHierarchicalMemory(
    persist_directory="./secure_memory",
    encryption_key="your-256-bit-key",
    encryption_algorithm="AES-256-GCM",
    trust_zone="confidential"
)
```

## Clear Memory

```python
memory.clear()
```

## Export/Import Memory

```python
# Export
memory.save("./memory_backup.json")

# Import
memory.load("./memory_backup.json")
```

## Memory with Trust Zones

```python
from rlm_toolkit.memory import SecureHierarchicalMemory, TrustZone

memory = SecureHierarchicalMemory(
    trust_zone=TrustZone(name="confidential", level=2),
    audit_enabled=True
)
```

## Related

- [Concept: Memory](../concepts/memory.md)
- [Tutorial: Memory Systems](../tutorials/05-memory.md)
- [Tutorial: H-MEM](../tutorials/07-hmem.md)
