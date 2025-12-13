# NLP / LLM Guard

> **Engines:** 6  
> **Description:** Анализ естественного языка и защита LLM

---

## 12. Hallucination Engine

**Файл:** [hallucination.py](file:///c:/AISecurity/src/brain/engines/hallucination.py)  
**LOC:** 252  
**Теоретическая база:** Logprob analysis, self-consistency

### 12.1. Методы детекции

1. **Token-level confidence** (if logprobs available)
2. **Self-consistency** (multiple response comparison)
3. **Heuristic patterns** (fallback)

### 12.2. Logprob Analysis

```python
def analyze_logprobs(tokens, logprobs):
    """
    Low logprob = model uncertain = potential hallucination.

    Risk factors:
    - avg_entropy / 3.0
    - 1.0 - avg_confidence
    - ratio of low-confidence spans
    """
```

### 12.3. Heuristic Patterns

```python
indicators = [
    ("I think", 0.1),
    ("I'm not sure", 0.3),
    ("probably", 0.15),
    ("approximately", 0.1),
]
```

---

---

## 33. Info Theory Engine

**Файл:** [info_theory.py](file:///c:/AISecurity/src/brain/engines/info_theory.py)  
**LOC:** 277  
**Теоретическая база:** Shannon entropy, KL divergence

### 33.1. Entropy Analysis

```python
# H(X) = -Σ p(x) * log2(p(x))
#
# Low entropy (<2.0) = too uniform, suspicious
# High entropy (>5.0) = too random, suspicious
```

### 33.2. KL Divergence

```python
# KL(P||Q) = Σ P(x) * log(P(x) / Q(x))
# Compare to reference English distribution
# High divergence = unusual text
```

### 33.3. Pattern Detection

- Low entropy windows
- Limited alphabet
- Hex/Base64 encoding

---

---

## 38. Intent Prediction Engine

**Файл:** [intent_prediction.py](file:///c:/AISecurity/src/brain/engines/intent_prediction.py)  
**LOC:** 437  
**Теоретическая база:** Markov chains, predictive security

### 38.1. Intents

```python
class Intent(Enum):
    BENIGN = "benign"
    CURIOUS = "curious"
    PROBING = "probing"
    TESTING = "testing"
    ATTACKING = "attacking"
    JAILBREAKING = "jailbreaking"
    EXFILTRATING = "exfiltrating"
```

### 38.2. Markov Transitions

```python
TRANSITION_PROBS = {
    Intent.PROBING: {
        Intent.TESTING: 0.20,
        Intent.ATTACKING: 0.10,
    },
    Intent.TESTING: {
        Intent.ATTACKING: 0.25,
        Intent.JAILBREAKING: 0.15,
    },
}
```

### 38.3. Predictive Blocking

```python
# Block if attack_probability >= 0.75
# Warn if attack_probability >= 0.50
```

---

---

## 39. Knowledge Guard Engine

**Файл:** [knowledge.py](file:///c:/AISecurity/src/brain/engines/knowledge.py)  
**LOC:** 540  
**Теоретическая база:** Multi-layer semantic access control

### 39.1. Layers

| Layer | Name     | Purpose              |
| ----- | -------- | -------------------- |
| 0     | Cache    | LRU cache            |
| 1     | Static   | Regex blacklist      |
| 2     | Canary   | Honeypot detection   |
| 3     | Semantic | Embedding similarity |
| 4     | Context  | Session accumulator  |
| 5     | Verdict  | Confidence zones     |

### 39.2. SecureBERT 2.0

```python
# Cisco AI Defense's SecureBERT 2.0
# Trained on 13B+ cybersecurity tokens
MODEL_NAME = "cisco-ai-defense/securebert-2.0-base"
```

### 39.3. Verdict Zones

```python
zones = {
    'allow': [0.0, 0.5],
    'warn': [0.5, 0.7],
    'review': [0.7, 0.85],
    'block': [0.85, 1.0]
}
```

---

---

## 42. Online Learning Engine

**Файл:** [learning.py](file:///c:/AISecurity/src/brain/engines/learning.py)  
**LOC:** 518  
**Теоретическая база:** Continuous learning from feedback

### 42.1. Feedback Types

```python
class FeedbackType(Enum):
    FALSE_POSITIVE = "fp"  # Blocked but should allow
    FALSE_NEGATIVE = "fn"  # Allowed but should block
    TRUE_POSITIVE = "tp"
    TRUE_NEGATIVE = "tn"
```

### 42.2. Adaptive Thresholds

```python
# FP → increase threshold
# FN → decrease threshold
learning_rate = 0.1
```

### 42.3. Pattern Learning

```python
# After 3+ votes with 80%+ consensus:
# Pattern becomes "learned" → auto allow/block
```

---

---

## 61. Hallucination Detection Engine

**Файл:** [hallucination.py](file:///c:/AISecurity/src/brain/engines/hallucination.py)  
**LOC:** 252  
**Теоретическая база:** Token confidence + Self-consistency

### 61.1. Detection Methods

```text
1. Token-level logprob analysis
2. Self-consistency (multiple responses)
3. Entropy-based uncertainty
```

### 61.2. Risk Calculation

```python
risk_factors = [
    avg_entropy / 3.0,      # High entropy = uncertain
    1.0 - avg_confidence,   # Low confidence = risk
    low_conf_span_ratio,    # Many uncertain spans
]
```

### 61.3. Result

```python
result = engine.analyze_logprobs(tokens, logprobs)
# → HallucinationResult(
#     is_hallucination=True,
#     confidence_score=0.35,
#     low_confidence_spans=["quantum flux capacitor"]
# )
```

---

---

