# Tutorial 5: Memory Systems

Deep dive into RLM-Toolkit's memory systems for building AI applications that remember.

## Memory Types Overview

| Type | Use Case | Persistence | Best For |
|------|----------|-------------|----------|
| **BufferMemory** | Simple chat | Session | Basic chatbots |
| **EpisodicMemory** | Entity tracking | Session | Customer service |
| **HierarchicalMemory** | Complex apps | Cross-session | Advanced assistants |
| **SecureHierarchicalMemory** | Sensitive data | Encrypted | Enterprise apps |

## BufferMemory

Simple conversation buffer:

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import BufferMemory

# Create buffer memory
memory = BufferMemory(
    max_messages=100,       # Keep last 100 messages
    return_messages=True    # Return as message objects
)

rlm = RLM.from_openai("gpt-4o", memory=memory)

# Messages are stored
rlm.run("Hello, I'm Alice")
rlm.run("I work at TechCorp")

# Access memory
for msg in memory.get_messages():
    print(f"{msg.role}: {msg.content}")
```

### BufferMemory Options

```python
# Token-limited buffer
memory = BufferMemory(
    max_tokens=4000,  # Limit by tokens instead of messages
    model="gpt-4o"    # For token counting
)

# Summary buffer - summarizes old messages
memory = BufferMemory(
    max_messages=20,
    summarize_after=10,     # Summarize when over 10 messages
    summary_llm=provider    # LLM for summarization
)
```

## EpisodicMemory

Stores information as entity-fact pairs:

```python
from rlm_toolkit.memory import EpisodicMemory

memory = EpisodicMemory()
rlm = RLM.from_openai("gpt-4o", memory=memory)

# Store facts about entities
rlm.run("John is 30 years old and works at Google")
rlm.run("Mary is John's wife. She's a doctor.")
rlm.run("They live in San Francisco")

# Memory stores:
# Entity: John -> age: 30, employer: Google
# Entity: Mary -> relationship: John's wife, profession: doctor
# Entity: John, Mary -> location: San Francisco

# Query specific entities
result = rlm.run("Where does John work?")
# Uses entity lookup for fast retrieval
```

### Manual Entity Access

```python
# Get all entities
entities = memory.get_entities()
print(entities)  # ['John', 'Mary']

# Get facts about entity
facts = memory.get_entity_facts("John")
print(facts)  # {'age': '30', 'employer': 'Google'}

# Add facts manually
memory.add_fact("John", "hobby", "tennis")
```

## HierarchicalMemory (H-MEM)

4-level memory with LLM-based consolidation:

```python
from rlm_toolkit.memory import HierarchicalMemory

memory = HierarchicalMemory(
    # Level 0: Episodes (raw messages)
    episode_limit=100,
    
    # Level 1: Traces (grouped by topic)
    trace_limit=50,
    
    # Level 2: Categories (summarized concepts)
    category_limit=20,
    
    # Level 3: Domain (meta-knowledge)
    domain_limit=10,
    
    # Consolidation settings
    consolidation_enabled=True,
    consolidation_threshold=20,  # Consolidate after 20 episodes
    consolidation_llm=None       # Uses main LLM if not specified
)

rlm = RLM.from_openai("gpt-4o", memory=memory)
```

### Memory Levels Explained

```
┌─────────────────────────────────────────────────────────────────┐
│                    H-MEM Architecture                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Level 0: Episode    "User said: my name is Alex"               │
│      ↓ consolidation                                            │
│  Level 1: Trace      "User: Alex, profession: engineer"         │
│      ↓ consolidation                                            │
│  Level 2: Category   "User profile and preferences"             │
│      ↓ consolidation                                            │
│  Level 3: Domain     "Technical user interested in AI"          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Persistence

```python
# Persist to disk
memory = HierarchicalMemory(
    persist_directory="./memory_store",
    auto_save=True,         # Save after each update
    save_interval=60        # Or save every 60 seconds
)

# Later, load from disk
memory2 = HierarchicalMemory(
    persist_directory="./memory_store"
)
# Automatically loads existing memory
```

### Cross-Session Memory

```python
# Session 1
memory = HierarchicalMemory(persist_directory="./user_123_memory")
rlm = RLM.from_openai("gpt-4o", memory=memory)
rlm.run("I prefer dark mode and Python programming")
# Memory saved automatically

# Session 2 (days later)
memory = HierarchicalMemory(persist_directory="./user_123_memory")
rlm = RLM.from_openai("gpt-4o", memory=memory)
result = rlm.run("What are my preferences?")
# Remembers: dark mode, Python
```

## SecureHierarchicalMemory

Encrypted memory with trust zones:

```python
from rlm_toolkit.memory import SecureHierarchicalMemory

memory = SecureHierarchicalMemory(
    # Encryption
    encryption_key="your-32-byte-encryption-key-here",
    encryption_algorithm="AES-256-GCM",
    
    # Trust zones
    trust_zone="confidential",  # public, internal, confidential, secret
    
    # Audit
    audit_enabled=True,
    audit_log_path="./memory_audit.log",
    
    # Persistence
    persist_directory="./secure_memory"
)

rlm = RLM.from_openai("gpt-4o", memory=memory)
```

### Trust Zones

```python
# Define trust zone access
from rlm_toolkit.memory import TrustZone

zones = {
    "public": TrustZone(
        name="public",
        access_level=0,
        can_share=True
    ),
    "internal": TrustZone(
        name="internal",
        access_level=1,
        can_share=False
    ),
    "confidential": TrustZone(
        name="confidential",
        access_level=2,
        requires_encryption=True
    ),
    "secret": TrustZone(
        name="secret",
        access_level=3,
        requires_encryption=True,
        audit_required=True
    )
}

memory = SecureHierarchicalMemory(
    trust_zones=zones,
    default_zone="internal"
)
```

## Memory Integration

### With RAG

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import HierarchicalMemory
from rlm_toolkit.vectorstores import ChromaVectorStore

# Memory for conversation context
memory = HierarchicalMemory()

# Vector store for document retrieval
vectorstore = ChromaVectorStore.from_documents(docs, embeddings)

# Combine both
rlm = RLM.from_openai(
    "gpt-4o",
    memory=memory,
    retriever=vectorstore.as_retriever()
)
```

### With Agents

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import HierarchicalMemory
from rlm_toolkit.tools import Calculator, WebSearch

memory = HierarchicalMemory(
    persist_directory="./agent_memory"
)

rlm = RLM.from_openai(
    "gpt-4o",
    memory=memory,
    tools=[Calculator(), WebSearch()]
)

# Memory persists across tool usage
rlm.run("Calculate 15% of 200")
rlm.run("Now search for that amount in dollars")  # Remembers: 30
```

## Memory Best Practices

!!! tip "Choose the Right Memory"
    - Simple chatbot: `BufferMemory`
    - CRM/Customer service: `EpisodicMemory`
    - Personal assistant: `HierarchicalMemory`
    - Enterprise: `SecureHierarchicalMemory`

!!! tip "Memory Limits"
    Set appropriate limits to avoid context overflow:
    ```python
    memory = HierarchicalMemory(
        episode_limit=100,
        context_token_limit=4000
    )
    ```

!!! tip "Consolidation"
    Enable consolidation for long-running apps:
    ```python
    memory = HierarchicalMemory(
        consolidation_enabled=True,
        consolidation_threshold=20
    )
    ```

!!! warning "Privacy"
    For sensitive data, always use `SecureHierarchicalMemory` with encryption.

## Next Steps

- [Tutorial 6: InfiniRetri](06-infiniretri.md)
- [Concept: H-MEM Architecture](../concepts/hmem.md)
- [Concept: Memory Systems](../concepts/memory.md)
