# H-MEM Concept

H-MEM (Hierarchical Memory) is RLM-Toolkit's 4-level memory architecture with LLM-based consolidation.

## The Problem

Traditional AI memory is flat:
- Buffer memory: Limited history
- Entity memory: Only facts, no context
- No long-term learning

## The Solution: H-MEM

4-level hierarchy mimicking human memory:

```
┌─────────────────────────────────────────────────────────────────┐
│                    H-MEM 4 Levels                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Level 3: Domain      │ Meta-knowledge, user profile            │
│  └── "Technical user, prefers Python, works in ML"             │
│           ↑ consolidation                                       │
│                                                                  │
│  Level 2: Category    │ Summarized concepts                     │
│  └── "User preferences: dark mode, detailed explanations"      │
│           ↑ consolidation                                       │
│                                                                  │
│  Level 1: Trace       │ Entity-fact groupings                   │
│  └── {user: "Alex", skills: ["Python", "ML"]}                   │
│           ↑ consolidation                                       │
│                                                                  │
│  Level 0: Episode     │ Raw conversation messages               │
│  └── "User: I've been coding in Python for 5 years"            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## How Consolidation Works

1. **Episode Accumulation**: Raw messages stored
2. **Threshold Trigger**: After N episodes, consolidation starts
3. **LLM Summarization**: LLM extracts key information
4. **Trace Creation**: Grouped by topic/entity
5. **Category Formation**: Higher-level concepts
6. **Domain Building**: Meta-knowledge about user

## Benefits

| Feature | Benefit |
|---------|---------|
| **Long-term Memory** | Remembers across sessions |
| **Efficient Storage** | Compressed at higher levels |
| **Context-Aware** | Adapts to user over time |
| **Persistent** | Saved to disk |

## Configuration

```python
from rlm_toolkit.memory import HierarchicalMemory, HMEMConfig

config = HMEMConfig(
    episode_limit=100,
    trace_limit=50,
    category_limit=20,
    domain_limit=10,
    consolidation_enabled=True,
    consolidation_threshold=25
)

memory = HierarchicalMemory(
    config=config,
    persist_directory="./memory"
)
```

## Related

- [Tutorial: H-MEM](../tutorials/07-hmem.md)
- [Tutorial: Memory Systems](../tutorials/05-memory.md)
