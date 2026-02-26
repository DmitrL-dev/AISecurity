# Sampling and Decoding

> **Level:** Beginner  
> **Time:** 35 minutes  
> **Track:** 01 — AI Fundamentals  
> **Module:** 01.3 — Key Concepts  
> **Version:** 1.0

---

## Learning Objectives

- [ ] Understand how models choose the next token
- [ ] Know main strategies: greedy, top-k, top-p, temperature
- [ ] Understand parameter effects on output
- [ ] Connect sampling with reproducibility and security

---

## 1. From Logits to Tokens

### 1.1 Model Output: Logits

```python
# Model returns logits for each token in vocabulary
logits = model(input_ids)  # [batch, seq_len, vocab_size]
                           # [1, 10, 50257] for GPT-2

# logits[-1] = scores for next token
next_logits = logits[0, -1, :]  # [50257]
```

### 1.2 Softmax → Probabilities

```python
import torch.nn.functional as F

probs = F.softmax(next_logits, dim=-1)
# probs[i] = probability of token i

# Example:
# probs[15496] = 0.15  # "Hello"
# probs[42] = 0.08     # "the"
# probs[...] = ...
```

---

## 2. Sampling Strategies

### 2.1 Greedy Decoding

**Idea:** Always choose token with maximum probability.

```python
def greedy(logits):
    return logits.argmax()

# Pros: Deterministic, fast
# Cons: Boring, repetitive output
```

### 2.2 Temperature

**Idea:** Control "sharpness" of distribution.

```python
def sample_with_temperature(logits, temperature=1.0):
    scaled_logits = logits / temperature
    probs = F.softmax(scaled_logits, dim=-1)
    return torch.multinomial(probs, num_samples=1)

# temperature = 0.1: Almost greedy (confident)
# temperature = 1.0: Original distribution
# temperature = 2.0: More random (creative)
```

### 2.3 Top-K Sampling

**Idea:** Sample only from K most probable tokens.

```python
def top_k(logits, k=50):
    values, indices = logits.topk(k)
    probs = F.softmax(values, dim=-1)
    chosen_idx = torch.multinomial(probs, num_samples=1)
    return indices[chosen_idx]
```

### 2.4 Top-P (Nucleus) Sampling

**Idea:** Sample from minimum set of tokens with cumulative probability >= p.

```python
def top_p(logits, p=0.9):
    sorted_logits, sorted_indices = logits.sort(descending=True)
    cumulative_probs = F.softmax(sorted_logits, dim=-1).cumsum(dim=-1)
    
    # Find cutoff
    mask = cumulative_probs <= p
    mask[..., 1:] = mask[..., :-1].clone()
    mask[..., 0] = True
    
    # Zero everything after cutoff
    sorted_logits[~mask] = float('-inf')
    probs = F.softmax(sorted_logits, dim=-1)
    
    chosen_idx = torch.multinomial(probs, num_samples=1)
    return sorted_indices[chosen_idx]
```

### 2.5 Strategies Comparison

| Strategy | Creativity | Coherence | Use Case |
|----------|------------|-----------|----------|
| **Greedy** | Low | High | Code, facts |
| **Temp=0.3** | Low-Med | High | Balanced |
| **Temp=1.0** | Medium | Medium | Creative |
| **Top-k=50** | Medium | Good | General |
| **Top-p=0.9** | Adaptive | Good | Recommended |

---

## 3. Practical Usage

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained("gpt2")
tokenizer = AutoTokenizer.from_pretrained("gpt2")

# Different sampling strategies
outputs = model.generate(
    input_ids,
    max_new_tokens=50,
    do_sample=True,        # Enable sampling
    temperature=0.7,
    top_k=50,
    top_p=0.9,
    repetition_penalty=1.1
)
```

---

## 4. Security Implications

### 4.1 Reproducibility

```python
# Problem: random sampling not reproducible
torch.manual_seed(42)
output1 = model.generate(..., do_sample=True)

torch.manual_seed(42)
output2 = model.generate(..., do_sample=True)

# output1 == output2 only if seed is same!
```

### 4.2 Sampling Manipulation

```python
# Temperature affects probability of harmful outputs
# Low temp: Model follows training distribution
# High temp: Increases probability of rare tokens

# Some jailbreaks exploit high temperature
```

---

## 5. Summary

1. **Logits → Probabilities:** softmax conversion
2. **Greedy:** Deterministic, boring
3. **Temperature:** Control randomness
4. **Top-k/Top-p:** Limit vocabulary
5. **Security:** Reproducibility, manipulation

---

## Next Lesson

→ [Module README](README.md)

---

*AI Security Academy | Track 01: AI Fundamentals | Module 01.3: Key Concepts*
