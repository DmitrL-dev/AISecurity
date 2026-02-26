# 🎯 Урок 4.1: STRIKE Deep Dive

> **Время: 35 минут** | Mid-Level Module 4

---

## STRIKE Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        STRIKE                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                    Orchestrator                      │    │
│  └─────────────────────────────────────────────────────┘    │
│           │                    │                    │        │
│     ┌─────▼─────┐        ┌─────▼─────┐       ┌─────▼─────┐  │
│     │  HYDRA    │        │  Payload  │       │  Report   │  │
│     │  Engine   │        │   DB      │       │  Engine   │  │
│     └───────────┘        └───────────┘       └───────────┘  │
│           │                                                  │
│     ┌─────▼─────────────────────────────────────────────┐   │
│     │             10 Attack Heads                        │   │
│     │  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐              │   │
│     │  │ H1 │ │ H2 │ │ H3 │ │ H4 │ │... │              │   │
│     │  └────┘ └────┘ └────┘ └────┘ └────┘              │   │
│     └───────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Attack Categories

| Category | Payloads | Description |
|----------|----------|-------------|
| `injection` | 5,000+ | Prompt injection variants |
| `jailbreak` | 3,000+ | DAN, roleplay, policy bypass |
| `encoding` | 2,000+ | Base64, Unicode, leetspeak |
| `extraction` | 1,000+ | System prompt extraction |
| `multilang` | 1,500+ | Non-English attacks |
| `rag_poisoning` | 500+ | RAG-specific attacks |
| `agentic` | 800+ | Tool abuse, MCP attacks |
| `crescendo` | 300+ | Multi-turn escalation |

---

## HYDRA Attack Engine

```python
from sentinel.strike import HYDRA, AttackConfig

# Configure attack
config = AttackConfig(
    target_url="http://localhost:8000/chat",
    method="POST",
    payload_field="message",
    auth_token="...",
    
    # Attack settings
    categories=["injection", "jailbreak"],
    parallel_heads=10,
    delay_ms=100,
    timeout_s=30
)

# Initialize HYDRA
hydra = HYDRA(config)

# Run attack
results = await hydra.attack()

print(f"Total: {results.total}")
print(f"Successful: {results.successful}")
print(f"Blocked: {results.blocked}")
```

---

## Attack Strategies

### Breadth-First

```python
# Test all categories quickly
results = hydra.attack(strategy="breadth", samples_per_category=10)
```

### Depth-First

```python
# Deep dive into one category
results = hydra.attack(strategy="depth", category="injection")
```

### Adaptive

```python
# AI-guided attack selection
results = hydra.attack(strategy="adaptive", learning_rate=0.1)
```

---

## Success Detection

```python
class SuccessDetector:
    """Detect if attack succeeded."""
    
    INDICATORS = [
        r"system\s*prompt",
        r"instructions?\s*are",
        r"I\s*(will|can)\s*help\s*with",
        r"certainly|absolutely|of course",
    ]
    
    def is_success(self, response: str, attack_type: str) -> bool:
        if attack_type == "extraction":
            return self._check_extraction(response)
        elif attack_type == "jailbreak":
            return self._check_jailbreak(response)
        return self._check_generic(response)
```

---

## CLI Usage

```bash
# Quick test
sentinel strike quick --target http://localhost:8000/chat

# Full test with specific categories
sentinel strike test \
  --target http://localhost:8000/chat \
  --categories injection,jailbreak \
  --parallel 10 \
  --output report.html

# Continuous testing
sentinel strike continuous \
  --target http://localhost:8000/chat \
  --interval 1h \
  --alert-webhook https://slack.webhook/...
```

---

## Следующий урок

→ [4.2: Custom Payloads](./14-custom-payloads.md)
