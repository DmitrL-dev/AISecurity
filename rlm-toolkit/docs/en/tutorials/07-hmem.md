# Tutorial 7: Hierarchical Memory (H-MEM)

Build AI systems with human-like memory using 4-level hierarchical architecture.

## What is H-MEM?

H-MEM is a revolutionary memory system that:

- **4 memory levels**: Episode → Trace → Category → Domain
- **LLM-based consolidation**: Automatic summarization across levels
- **Cross-session persistence**: Remember across conversations
- **Security integration**: Trust zones and encryption

## H-MEM Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    H-MEM 4-Level Architecture                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Level 0: Episode     │ Raw messages, high detail               │
│  └── "User: My name is Alex, I'm an engineer at Google"        │
│           ↓ consolidation (every N episodes)                    │
│                                                                  │
│  Level 1: Trace       │ Grouped by topic/entity                 │
│  └── {entity: "Alex", facts: [engineer, Google, ...]}           │
│           ↓ consolidation (every N traces)                      │
│                                                                  │
│  Level 2: Category    │ Summarized concepts                     │
│  └── "User is a technical professional in big tech"            │
│           ↓ consolidation (every N categories)                  │
│                                                                  │
│  Level 3: Domain      │ Meta-knowledge / user profile           │
│  └── "Technical user, prefers detailed explanations"           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

```bash
pip install rlm-toolkit[all]
export OPENAI_API_KEY=your-key
```

## Step 1: Basic H-MEM

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import HierarchicalMemory

# Create H-MEM
memory = HierarchicalMemory()

rlm = RLM.from_openai("gpt-4o", memory=memory)

# Have a conversation
rlm.run("Hi, I'm Sarah. I work as a data scientist at Netflix.")
rlm.run("I specialize in recommendation systems.")
rlm.run("I prefer Python and TensorFlow.")

# Query accumulated knowledge
result = rlm.run("What do you know about me?")
print(result.final_answer)
# "You're Sarah, a data scientist at Netflix specializing in 
#  recommendation systems. You prefer Python and TensorFlow."
```

## Step 2: Consolidation Configuration

```python
from rlm_toolkit.memory import HierarchicalMemory, HMEMConfig

config = HMEMConfig(
    # Level limits before consolidation
    episode_limit=50,     # Consolidate episodes after 50
    trace_limit=20,       # Consolidate traces after 20
    category_limit=10,
    domain_limit=5,
    
    # Consolidation settings
    consolidation_enabled=True,
    consolidation_threshold=20,   # Trigger at 20 episodes
    consolidation_llm=None,       # Use main LLM
    
    # Context limits
    max_context_tokens=4000,      # Max tokens to include in prompt
)

memory = HierarchicalMemory(config=config)
```

## Step 3: Manual Level Inspection

```python
from rlm_toolkit.memory import HierarchicalMemory

memory = HierarchicalMemory()
rlm = RLM.from_openai("gpt-4o", memory=memory)

# After some conversation...

# Inspect each level
print("Episode Level:")
for episode in memory.get_episodes(limit=5):
    print(f"  {episode.content[:100]}...")

print("\nTrace Level:")
for trace in memory.get_traces():
    print(f"  {trace.topic}: {trace.summary}")

print("\nCategory Level:")
for category in memory.get_categories():
    print(f"  {category.name}: {category.description}")

print("\nDomain Level:")
domain = memory.get_domain()
print(f"  {domain.profile}")
```

## Step 4: Persistence

```python
from rlm_toolkit.memory import HierarchicalMemory

# Session 1: Create and save
memory = HierarchicalMemory(
    persist_directory="./user_memories/user_123",
    auto_save=True
)

rlm = RLM.from_openai("gpt-4o", memory=memory)
rlm.run("Remember that I love hiking and photography")
# Automatically saved

# Session 2: Load and continue
memory2 = HierarchicalMemory(
    persist_directory="./user_memories/user_123"
)

rlm2 = RLM.from_openai("gpt-4o", memory=memory2)
result = rlm2.run("What are my hobbies?")
# "Your hobbies include hiking and photography!"
```

## Step 5: Secure H-MEM with Trust Zones

```python
from rlm_toolkit.memory import SecureHierarchicalMemory

memory = SecureHierarchicalMemory(
    # Encryption
    encryption_key="your-256-bit-key-here",
    
    # Trust zone
    trust_zone="confidential",  # public, internal, confidential, secret
    
    # Audit
    audit_enabled=True,
    audit_log_path="./memory_audit.log",
    
    persist_directory="./secure_memory"
)

rlm = RLM.from_openai("gpt-4o", memory=memory)

# Sensitive data is encrypted at rest
rlm.run("My SSN is 123-45-6789")  # Encrypted in storage
```

## Step 6: Memory Sharing Between Agents

```python
from rlm_toolkit.memory import HierarchicalMemory, SharedMemoryPool

# Create shared memory pool
pool = SharedMemoryPool(
    trust_level="internal",
    sync_interval=30  # Sync every 30 seconds
)

# Agent 1: Customer service
agent1_memory = HierarchicalMemory(
    agent_id="customer_service",
    shared_pool=pool,
    share_levels=[2, 3]  # Share Category and Domain only
)

# Agent 2: Technical support
agent2_memory = HierarchicalMemory(
    agent_id="tech_support",
    shared_pool=pool,
    share_levels=[2, 3]
)

# Both agents share high-level user knowledge
# But keep conversation details private
```

## Step 7: Custom Consolidation

```python
from rlm_toolkit.memory import HierarchicalMemory, ConsolidationStrategy

# Custom consolidation prompts
class CustomConsolidator(ConsolidationStrategy):
    def consolidate_episodes_to_trace(self, episodes):
        """Custom logic for episode consolidation."""
        prompt = f"""Analyze these conversation episodes and extract:
        1. Key entities mentioned
        2. Important facts
        3. User preferences
        
        Episodes:
        {episodes}
        
        Output as JSON."""
        
        return self.llm.generate(prompt)
    
    def consolidate_traces_to_category(self, traces):
        """Custom trace consolidation."""
        # Your logic here
        pass

memory = HierarchicalMemory(
    consolidation_strategy=CustomConsolidator()
)
```

## Complete Application: Personal Assistant

```python
# personal_assistant.py
from rlm_toolkit import RLM
from rlm_toolkit.memory import HierarchicalMemory, HMEMConfig
from rlm_toolkit.tools import Calculator, WebSearch, DateTimeTool
import os

class PersonalAssistant:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.memory_path = f"./memories/{user_id}"
        
        # Configure H-MEM
        config = HMEMConfig(
            episode_limit=100,
            consolidation_enabled=True,
            consolidation_threshold=25
        )
        
        self.memory = HierarchicalMemory(
            config=config,
            persist_directory=self.memory_path,
            auto_save=True
        )
        
        # Create RLM with memory and tools
        self.rlm = RLM.from_openai(
            "gpt-4o",
            memory=self.memory,
            tools=[Calculator(), WebSearch(), DateTimeTool()],
            system_prompt=self._create_system_prompt()
        )
    
    def _create_system_prompt(self):
        """Generate system prompt with user profile."""
        domain = self.memory.get_domain()
        
        base = """You are a helpful personal assistant.
You remember all previous conversations with the user.
Use your knowledge of the user to personalize responses."""
        
        if domain and domain.profile:
            base += f"\n\nUser Profile:\n{domain.profile}"
        
        return base
    
    def chat(self, message: str) -> str:
        """Process a chat message."""
        result = self.rlm.run(message)
        return result.final_answer
    
    def get_memory_stats(self) -> dict:
        """Get current memory statistics."""
        return {
            "episodes": len(self.memory.get_episodes()),
            "traces": len(self.memory.get_traces()),
            "categories": len(self.memory.get_categories()),
            "has_domain": self.memory.get_domain() is not None
        }
    
    def forget(self, topic: str = None):
        """Selectively forget information."""
        if topic:
            self.memory.forget_topic(topic)
        else:
            self.memory.clear()

def main():
    import sys
    user_id = sys.argv[1] if len(sys.argv) > 1 else "default"
    
    print(f"🧠 Personal Assistant for {user_id}")
    print("   Commands: 'stats', 'forget', 'quit'\n")
    
    assistant = PersonalAssistant(user_id)
    
    while True:
        user_input = input("You: ").strip()
        
        if not user_input:
            continue
        
        if user_input == 'quit':
            break
        
        if user_input == 'stats':
            stats = assistant.get_memory_stats()
            print(f"📊 Memory: {stats}")
            continue
        
        if user_input.startswith('forget'):
            topic = user_input[6:].strip() or None
            assistant.forget(topic)
            print("🧹 Memory cleared")
            continue
        
        response = assistant.chat(user_input)
        print(f"Assistant: {response}\n")

if __name__ == "__main__":
    main()
```

## Best Practices

!!! tip "Consolidation Threshold"
    Set based on conversation frequency:
    - High frequency: 50-100 episodes
    - Low frequency: 10-20 episodes

!!! tip "Trust Zones"
    Use appropriate zones:
    - `public`: Non-sensitive, shareable
    - `internal`: Business data
    - `confidential`: Personal info
    - `secret`: Highly sensitive

!!! tip "Memory Cleanup"
    Implement periodic cleanup:
    ```python
    memory.cleanup_old_episodes(days=30)
    ```

!!! warning "Storage"
    H-MEM grows over time. Monitor disk usage and implement archival strategies.

## Next Steps

- [Tutorial 8: Self-Evolving](08-self-evolving.md)
- [Concept: H-MEM Architecture](../concepts/hmem.md)
- [Concept: Security](../concepts/security.md)
