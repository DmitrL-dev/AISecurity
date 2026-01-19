# Tutorial 11: Prompt Optimization with DSPy

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> Learn to automatically optimize prompts for better accuracy

## What You'll Learn

- Create DSPy signatures
- Use ChainOfThought for reasoning
- Optimize with BootstrapFewShot
- Measure improvements

## Prerequisites

```bash
pip install rlm-toolkit
```

## Part 1: Problem Setup

We'll build a customer support classifier that improves itself.

### 1.1 Define the Task

```python
from rlm_toolkit.optimize import Signature, Example

# Define what we want
sig = Signature(
    inputs=["ticket"],
    outputs=["category", "priority"],
    instructions="Classify support ticket"
)

# Create training examples
trainset = [
    Example(
        ticket="My order hasn't arrived in 2 weeks",
        category="shipping",
        priority="high"
    ),
    Example(
        ticket="How do I change my password?",
        category="account",
        priority="low"
    ),
    Example(
        ticket="App crashes when I open settings",
        category="bug",
        priority="high"
    ),
    Example(
        ticket="What are your business hours?",
        category="general",
        priority="low"
    ),
    # Add 20+ more for best results
]
```

---

## Part 2: Baseline Model

### 2.1 Simple Predictor

```python
from rlm_toolkit.optimize import Predict
from rlm_toolkit.providers import OpenAIProvider

provider = OpenAIProvider("gpt-4o")
baseline = Predict(sig, provider)

# Test it
result = baseline(ticket="I can't log into my account")
print(f"Category: {result['category']}")
print(f"Priority: {result['priority']}")
```

### 2.2 Measure Baseline

```python
def evaluate(model, testset):
    correct = 0
    for example in testset:
        pred = model(ticket=example.ticket)
        if pred["category"] == example.category:
            correct += 1
    return correct / len(testset)

baseline_accuracy = evaluate(baseline, testset)
print(f"Baseline: {baseline_accuracy:.1%}")  # ~65%
```

---

## Part 3: Add Reasoning

### 3.1 ChainOfThought

```python
from rlm_toolkit.optimize import ChainOfThought

cot = ChainOfThought(sig, provider)

result = cot(ticket="My payment was charged twice")
print(f"Reasoning: {result['reasoning']}")
print(f"Category: {result['category']}")
print(f"Priority: {result['priority']}")
```

### 3.2 Measure Improvement

```python
cot_accuracy = evaluate(cot, testset)
print(f"ChainOfThought: {cot_accuracy:.1%}")  # ~75%
```

---

## Part 4: Automatic Optimization

### 4.1 BootstrapFewShot

```python
from rlm_toolkit.optimize import BootstrapFewShot

def category_match(pred, gold):
    return pred["category"] == gold.category

optimizer = BootstrapFewShot(
    metric=category_match,
    num_candidates=10
)

optimized = optimizer.compile(
    ChainOfThought(sig, provider),
    trainset=trainset
)
```

### 4.2 Final Evaluation

```python
optimized_accuracy = evaluate(optimized, testset)
print(f"Optimized: {optimized_accuracy:.1%}")  # ~92%

print(f"""
Improvement Summary
-------------------
Baseline:     {baseline_accuracy:.1%}
ChainOfThought: {cot_accuracy:.1%}
Optimized:    {optimized_accuracy:.1%}

Gain: +{(optimized_accuracy - baseline_accuracy) * 100:.0f}%
""")
```

---

## Part 5: Production Deployment

### 5.1 Save Optimized Model

```python
import pickle

with open("classifier_v1.pkl", "wb") as f:
    pickle.dump(optimized, f)
```

### 5.2 Load and Use

```python
with open("classifier_v1.pkl", "rb") as f:
    classifier = pickle.load(f)

# Production use
result = classifier(ticket="Where is my refund?")
print(f"→ {result['category']} ({result['priority']})")
```

---

## Results

| Model | Accuracy | Latency |
|-------|----------|---------|
| Baseline | 65% | 0.5s |
| ChainOfThought | 75% | 1.2s |
| **Optimized** | **92%** | 1.0s |

---

## Next Steps

- [Concept: Prompt Optimization](../concepts/optimize.md)
- [Tutorial: Observability](12-observability.md)
- [Tutorial: Self-Evolving](08-self-evolving.md)
