# Memory Systems

RLM-Toolkit provides comprehensive memory management from simple buffers to advanced hierarchical systems.

## Memory Types

### Overview

| Type | Persistence | Complexity | Use Case |
|------|-------------|------------|----------|
| **BufferMemory** | Session | Simple | Short conversations |
| **SummaryMemory** | Session | Medium | Long conversations |
| **EntityMemory** | Session | Medium | Entity tracking |
| **EpisodicMemory** | Persistent | Medium | Cross-session |
| **HierarchicalMemory (H-MEM)** | Persistent | High | Long-term learning |
| **SecureHierarchicalMemory** | Persistent | High | Enterprise security |

## BufferMemory

Stores raw conversation history.

```python
from rlm_toolkit.memory import BufferMemory

memory = BufferMemory(
    max_messages=100,      # Keep last 100 messages
    return_messages=True   # Return as Message objects
)

# Add messages
memory.add_user_message("Hello!")
memory.add_ai_message("Hi! How can I help?")

# Get history
history = memory.get_history()
print(history)
# [Message(role='user', content='Hello!'), 
#  Message(role='ai', content='Hi! How can I help?')]

# Use with RLM
rlm = RLM.from_openai("gpt-4o", memory=memory)
```

### Token-Limited Buffer

```python
from rlm_toolkit.memory import TokenBufferMemory

memory = TokenBufferMemory(
    max_tokens=4000,           # Token limit
    model="gpt-4o",            # For tokenization
    overflow_strategy="oldest" # Remove oldest first
)
```

## SummaryMemory

Summarizes conversation when it gets too long.

```python
from rlm_toolkit.memory import SummaryMemory

memory = SummaryMemory(
    summarizer=RLM.from_openai("gpt-4o-mini"),
    max_tokens=2000,
    summary_prompt="Summarize this conversation concisely:"
)

# Automatically summarizes when exceeding max_tokens
for i in range(100):
    memory.add_user_message(f"Question {i}")
    memory.add_ai_message(f"Answer {i}")

# Get context (includes summary + recent messages)
context = memory.get_context()
```

## EntityMemory

Tracks entities mentioned in conversation.

```python
from rlm_toolkit.memory import EntityMemory

memory = EntityMemory(
    entity_extractor=RLM.from_openai("gpt-4o-mini")
)

memory.add_user_message("My name is Alex and I work at TechCorp")
memory.add_ai_message("Nice to meet you, Alex! Tell me more about TechCorp.")

# Access entities
print(memory.entities)
# {
#   "Alex": {"type": "person", "facts": ["works at TechCorp"]},
#   "TechCorp": {"type": "organization", "facts": ["Alex works here"]}
# }

# Query entities
print(memory.get_entity("Alex"))
```

## EpisodicMemory

Persistent memory across sessions.

```python
from rlm_toolkit.memory import EpisodicMemory

memory = EpisodicMemory(
    persist_directory="./memory",
    embedding=OpenAIEmbeddings(),
    max_episodes=1000
)

# Episodes are stored with timestamps
memory.add_episode(
    user_message="How do I configure Redis?",
    ai_response="Here's how to configure Redis...",
    metadata={"topic": "configuration"}
)

# Semantic retrieval of relevant episodes
relevant = memory.retrieve(
    query="Redis setup",
    k=5
)
```

## HierarchicalMemory (H-MEM)

4-level memory with LLM consolidation.

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
    persist_directory="./hmem",
    consolidator=RLM.from_openai("gpt-4o-mini")
)

# Add memories
memory.add_episode(user="I'm a Python developer", ai="Great!")
memory.add_episode(user="I use PyTorch for ML", ai="PyTorch is excellent!")

# After 25+ episodes, consolidation triggers:
# Episode → Trace → Category → Domain
# "Python developer, uses PyTorch" → "ML engineer profile"
```

### H-MEM Levels

```
┌─────────────────────────────────────────────────────────────────┐
│                    H-MEM Architecture                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Level 3: Domain                                                 │
│  └── "Technical user, ML focus, Python expert"                  │
│           ↑                                                      │
│  Level 2: Category                                               │
│  └── "Preferences: detailed explanations, code examples"        │
│           ↑                                                      │
│  Level 1: Trace                                                  │
│  └── {user: "Alex", skills: ["Python", "PyTorch"]}              │
│           ↑                                                      │
│  Level 0: Episode                                                │
│  └── "User: I've been coding Python for 5 years"                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## SecureHierarchicalMemory

H-MEM with encryption and trust zones.

```python
from rlm_toolkit.memory import SecureHierarchicalMemory, TrustZone

memory = SecureHierarchicalMemory(
    persist_directory="./secure_memory",
    encryption_key="your-256-bit-key",
    encryption_algorithm="AES-256-GCM",
    trust_zone=TrustZone(name="confidential", level=2),
    audit_enabled=True,
    audit_log_path="./audit.log"
)

# All data encrypted at rest
memory.add_episode(user="My SSN is 123-45-6789", ai="Noted.")

# Audit trail
# 2024-01-15T10:30:00Z ADD_EPISODE user=admin zone=confidential
```

### Trust Zones

| Zone | Level | Description |
|------|-------|-------------|
| `public` | 0 | Non-sensitive data |
| `internal` | 1 | Internal business data |
| `confidential` | 2 | Personal/sensitive data |
| `secret` | 3 | Highly restricted data |

## Memory with RLM

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import HierarchicalMemory

memory = HierarchicalMemory(persist_directory="./memory")
rlm = RLM.from_openai("gpt-4o", memory=memory)

# Memory automatically populated
response = rlm.run("Hi, I'm Alex, a Python developer")
response = rlm.run("What ML framework should I use?")
# AI remembers user is a Python developer
```

## Custom Memory

```python
from rlm_toolkit.memory import BaseMemory

class RedisMemory(BaseMemory):
    def __init__(self, redis_url: str):
        self.redis = Redis.from_url(redis_url)
    
    def add_message(self, role: str, content: str):
        self.redis.lpush("messages", f"{role}:{content}")
    
    def get_history(self) -> list:
        return self.redis.lrange("messages", 0, -1)
    
    def clear(self):
        self.redis.delete("messages")
```

## Best Practices

!!! tip "Memory Selection"
    - **Simple chatbots**: BufferMemory
    - **Long conversations**: SummaryMemory
    - **Entity-focused**: EntityMemory
    - **Cross-session**: EpisodicMemory
    - **Long-term learning**: HierarchicalMemory

!!! tip "Token Management"
    Use TokenBufferMemory to prevent context overflow:
    ```python
    memory = TokenBufferMemory(max_tokens=4000)
    ```

!!! tip "Persistence"
    Always set persist_directory for production:
    ```python
    memory = HierarchicalMemory(persist_directory="./memory")
    ```

## Related

- [Tutorial: Memory Systems](../tutorials/05-memory.md)
- [Tutorial: H-MEM](../tutorials/07-hmem.md)
- [Concept: H-MEM](./hmem.md)
- [Concept: Security](./security.md)
