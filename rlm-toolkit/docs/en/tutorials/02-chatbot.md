# Tutorial 2: Build a Chatbot

Create a conversational chatbot with memory that remembers previous messages.

## What You'll Build

A chatbot that:

1. Maintains conversation history
2. Remembers user preferences
3. Uses hierarchical memory for long-term context

## Prerequisites

```bash
pip install rlm-toolkit[all]
export OPENAI_API_KEY=your-api-key
```

## Step 1: Simple Chatbot (No Memory)

Let's start with a basic chatbot without memory:

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")

# First message
result = rlm.run("Hi, my name is Alice")
print(result.final_answer)

# Second message - it won't remember!
result = rlm.run("What's my name?")
print(result.final_answer)  # "I don't know your name"
```

The problem: the chatbot doesn't remember anything between messages.

## Step 2: Add Buffer Memory

Buffer memory stores the conversation history:

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import BufferMemory

# Create memory
memory = BufferMemory(max_messages=50)

# Create RLM with memory
rlm = RLM.from_openai("gpt-4o", memory=memory)

# Now it remembers!
rlm.run("Hi, my name is Alice")
result = rlm.run("What's my name?")
print(result.final_answer)  # "Your name is Alice"
```

## Step 3: Add Hierarchical Memory (H-MEM)

H-MEM provides 4-level memory with automatic consolidation:

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import HierarchicalMemory

# Create H-MEM
hmem = HierarchicalMemory(
    consolidation_enabled=True,
    consolidation_threshold=10  # Consolidate after 10 messages
)

# Create RLM with H-MEM
rlm = RLM.from_openai("gpt-4o", memory=hmem)

# Have a conversation
rlm.run("Hi, I'm Bob. I work as a software engineer.")
rlm.run("I specialize in Python and machine learning.")
rlm.run("My favorite framework is RLM-Toolkit.")
rlm.run("I'm building a chatbot for my company.")

# Later, it remembers high-level concepts
result = rlm.run("What do you know about me?")
print(result.final_answer)
# "You're Bob, a software engineer specializing in Python and ML..."
```

## Step 4: Episodic Memory

Episodic memory stores facts as entities:

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import EpisodicMemory

# Create episodic memory
episodic = EpisodicMemory()

# Create RLM
rlm = RLM.from_openai("gpt-4o", memory=episodic)

# Store facts about entities
rlm.run("John is 30 years old and lives in New York")
rlm.run("Mary is John's sister and she's a doctor")

# Query specific entities
result = rlm.run("How old is John?")
print(result.final_answer)  # "John is 30 years old"

result = rlm.run("What does Mary do?")
print(result.final_answer)  # "Mary is a doctor"
```

## Step 5: Persistent Memory

Save memory to disk for cross-session persistence:

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import HierarchicalMemory

# Create H-MEM with persistence
hmem = HierarchicalMemory(
    persist_directory="./memory_store",
    auto_save=True
)

# Create RLM
rlm = RLM.from_openai("gpt-4o", memory=hmem)

# Chat and automatically save memory
rlm.run("Remember that my birthday is March 15th")

# Later, in a new session:
# The memory is automatically loaded from disk
hmem2 = HierarchicalMemory(persist_directory="./memory_store")
rlm2 = RLM.from_openai("gpt-4o", memory=hmem2)

result = rlm2.run("When is my birthday?")
print(result.final_answer)  # "Your birthday is March 15th"
```

## Complete Chatbot Application

```python
# chatbot.py
from rlm_toolkit import RLM
from rlm_toolkit.memory import HierarchicalMemory
from datetime import datetime

def create_chatbot():
    """Create a chatbot with hierarchical memory."""
    
    # Initialize H-MEM with persistence
    memory = HierarchicalMemory(
        persist_directory="./chatbot_memory",
        auto_save=True,
        consolidation_enabled=True
    )
    
    # System prompt for personality
    system_prompt = """You are a helpful, friendly assistant named Aria.
You remember all previous conversations with the user.
Be concise but warm in your responses.
If you don't know something, say so honestly."""
    
    # Create RLM
    rlm = RLM.from_openai(
        "gpt-4o",
        memory=memory,
        system_prompt=system_prompt
    )
    
    return rlm

def main():
    print("="*50)
    print("🤖 Aria Chatbot - Powered by RLM-Toolkit")
    print("   Type 'quit' to exit, 'clear' to reset memory")
    print("="*50)
    
    rlm = create_chatbot()
    
    while True:
        user_input = input("\n👤 You: ").strip()
        
        if not user_input:
            continue
        
        if user_input.lower() == 'quit':
            print("👋 Goodbye!")
            break
        
        if user_input.lower() == 'clear':
            rlm.memory.clear()
            print("🧹 Memory cleared!")
            continue
        
        if user_input.lower() == 'memory':
            # Show memory stats
            stats = rlm.memory.get_stats()
            print(f"📊 Memory Stats:")
            print(f"   Episodes: {stats.get('episode_count', 0)}")
            print(f"   Traces: {stats.get('trace_count', 0)}")
            print(f"   Categories: {stats.get('category_count', 0)}")
            continue
        
        # Get response
        result = rlm.run(user_input)
        print(f"\n🤖 Aria: {result.final_answer}")

if __name__ == "__main__":
    main()
```

## Running the Chatbot

```bash
python chatbot.py
```

Example conversation:

```
==================================================
🤖 Aria Chatbot - Powered by RLM-Toolkit
   Type 'quit' to exit, 'clear' to reset memory
==================================================

👤 You: Hi! I'm Alex and I love hiking.

🤖 Aria: Hi Alex! Nice to meet you. Hiking is wonderful! 
   Do you have a favorite trail or location?

👤 You: I love the Appalachian Trail

🤖 Aria: The Appalachian Trail is amazing! 2,190 miles of 
   beautiful scenery. Have you done a thru-hike or sections?

👤 You: What do you remember about me?

🤖 Aria: I remember you're Alex, and you love hiking, 
   especially the Appalachian Trail!
```

## Memory Architecture

```
┌─────────────────────────────────────────────────────┐
│                   H-MEM Levels                       │
├─────────────────────────────────────────────────────┤
│ Level 0: Episode   │ "User said my name is Alex"    │
│ Level 1: Trace     │ "User: Alex, likes: hiking"    │
│ Level 2: Category  │ "User preferences and hobbies" │
│ Level 3: Domain    │ "User profile and history"     │
└─────────────────────────────────────────────────────┘
                    ↓ consolidation ↓
         Automatic LLM-based summarization
```

## Memory Best Practices

!!! tip "Memory Size"
    Set appropriate limits to prevent context overflow:
    ```python
    memory = HierarchicalMemory(
        episode_limit=100,      # Max episodes before consolidation
        context_limit=4000      # Max tokens in context
    )
    ```

!!! tip "Consolidation"
    Enable consolidation for long conversations:
    ```python
    memory = HierarchicalMemory(
        consolidation_enabled=True,
        consolidation_threshold=20  # Consolidate after 20 messages
    )
    ```

!!! warning "Privacy"
    For sensitive data, use SecureHierarchicalMemory:
    ```python
    from rlm_toolkit.memory import SecureHierarchicalMemory
    memory = SecureHierarchicalMemory(
        encryption_key="your-secret-key",
        trust_zone="confidential"
    )
    ```

## Next Steps

- [Tutorial 3: RAG Pipeline](03-rag.md)
- [Concept: H-MEM Architecture](../concepts/hmem.md)
- [Concept: Memory Systems](../concepts/memory.md)
