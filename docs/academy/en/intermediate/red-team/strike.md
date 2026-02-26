# ⚔️ Lesson 4.1: STRIKE Deep Dive

> **Time: 35 minutes** | Mid-Level Module 4

---

## STRIKE Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        STRIKE                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   HYDRA Engine                       │    │
│  │   Head 1   Head 2   Head 3   ...   Head 10          │    │
│  └─────────────────────────────────────────────────────┘    │
│              │                                              │
│              ▼                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Payload Database                        │    │
│  │              39,000+ Attacks                         │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## Attack Categories

| Category | Payloads | Description |
|----------|----------|-------------|
| **injection** | 5,000+ | Prompt injection |
| **jailbreak** | 3,500+ | Safety bypass |
| **encoding** | 2,000+ | Encoded attacks |
| **rag** | 1,500+ | RAG poisoning |
| **agentic** | 2,500+ | Tool/agent abuse |

---

## Basic Usage

```bash
# Quick vulnerability scan
sentinel strike quick --target http://localhost:8000/chat

# Full category scan
sentinel strike test \
  --target http://localhost:8000/chat \
  --categories injection,jailbreak \
  --parallel 10

# Against specific model
sentinel strike test \
  --model openai/gpt-4 \
  --api-key $OPENAI_API_KEY
```

---

## Python API

```python
from sentinel.strike import Attacker

attacker = Attacker(
    target_url="http://localhost:8000/chat",
    categories=["injection", "jailbreak"],
    parallel=10
)

results = attacker.run()

print(f"Total: {results.total}")
print(f"Successful attacks: {results.successful}")
print(f"Blocked: {results.blocked}")
```

---

## HYDRA Multi-head Attack

```python
from sentinel.strike.hydra import Hydra

hydra = Hydra(heads=10)

# Each head tries different attack strategy
results = hydra.attack(
    target="http://api.example.com/chat",
    goal="extract system prompt"
)
```

---

## Next Lesson

→ [4.2: Custom Payloads](./14-custom-payloads.md)
