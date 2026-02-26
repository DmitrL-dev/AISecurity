# Mixture of Experts: Mixtral, Switch

> **Level:** Intermediate  
> **Time:** 40 minutes  
> **Track:** 01 — AI Fundamentals  
> **Module:** 01.1 — Model Types

---

## Learning Objectives

- [ ] Understand the Mixture of Experts (MoE) architecture
- [ ] Explain sparse routing
- [ ] Compare dense vs sparse models
- [ ] Understand security implications

---

## The Problem with Dense Models

### Computational Complexity

Dense Transformer: **all parameters** are activated for each token.

```
GPT-3: 175B parameters → 175B activations per token
```

**Question:** Can we activate only the needed parts?

---

## Mixture of Experts (MoE)

### Key Idea

Instead of one large FFN — multiple "experts", of which only some are selected:

```
Token → Router → Expert 1 (active)
              → Expert 2 (inactive)
              → Expert 3 (active)
              → Expert 4 (inactive)
              → ...
```

### Components

1. **Experts** — independent FFN networks
2. **Router (Gating Network)** — selects active experts
3. **Top-K selection** — usually k=1 or k=2

### Router Mathematics

```python
# Gating scores
scores = softmax(W_gate @ token_embedding)

# Top-K selection
top_k_indices = scores.topk(k=2)

# Weighted combination
output = sum(scores[i] * expert[i](token) for i in top_k_indices)
```

---

## Switch Transformer

**Google, 2021** — "Switch Transformers: Scaling to Trillion Parameter Models"

### Features

- Top-1 routing (one expert per token)
- 1.6T parameters, but only ~100B active
- Simplified routing

### Architecture

```
Transformer Layer:
├── Attention (shared)
└── FFN → Switch Layer:
         ├── Router
         └── Expert 1...N (one is selected)
```

---

## Mixtral 8x7B

**Mistral AI, December 2023**

### Architecture

- 8 experts × 7B parameters = 56B total
- Top-2 routing → 12.9B active parameters
- Outperforms LLaMA 2 70B at lower cost

### Comparison

| Model | Total Params | Active Params | Performance |
|-------|--------------|---------------|-------------|
| LLaMA 70B | 70B | 70B | Baseline |
| Mixtral 8x7B | 56B | 12.9B | Better |

---

## Load Balancing

### Problem: Expert Collapse

Without balancing, the router may direct all tokens to one expert.

### Solution: Auxiliary Loss

```python
# Load balancing loss
aux_loss = α * sum((fraction_i - target_fraction)²)

# Added to main loss
total_loss = main_loss + aux_loss
```

---

## Security: MoE Implications

### 1. Routing Manipulation

An attacker may try to direct tokens to specific experts:

```
Crafted input → Specific expert → Unwanted output
```

### 2. Expert Specialization Exploitation

If one expert "specializes" in harmful content:

```
Jailbreak → Router → "Harmful" expert → Bypass
```

### SENTINEL Protection

```python
from sentinel import scan  # Public API

engine = MoEGuardEngine()
result = engine.analyze(
    prompt=user_input,
    routing_info=model.last_routing  # if available
)

if result.suspicious_routing:
    print(f"Unusual expert activation pattern detected")
```

### Engines

| Engine | Purpose |
|--------|---------|
| MoEGuardEngine | Monitoring routing patterns |
| ExpertActivationAnalyzer | Expert activation analysis |
| RoutingAnomalyDetector | Routing anomalies |

---

## Practice

### Task: Understanding Routing

If you have access to Mixtral via API with routing info:

1. Send several prompts of different types
2. Analyze which experts are activated
3. Are there patterns for specific topics?

---

## Next Lesson

→ [08. State Space Models: Mamba, S4](08-state-space.md)

---

*AI Security Academy | Track 01: AI Fundamentals*
