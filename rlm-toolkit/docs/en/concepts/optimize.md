# Prompt Optimization (DSPy)

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **Automatic prompt optimization** — Define what, not how

## Overview

RLM-Toolkit includes DSPy-style optimization:
- **Signatures** — Declarative input/output specifications
- **Modules** — Predict, ChainOfThought, SelfRefine
- **Optimizers** — BootstrapFewShot, PromptOptimizer

## Quick Start

```python
from rlm_toolkit.optimize import Signature, Predict
from rlm_toolkit.providers import OpenAIProvider

# Define signature
sig = Signature(
    inputs=["question", "context"],
    outputs=["answer"],
    instructions="Answer the question based on context"
)

# Create predictor
provider = OpenAIProvider("gpt-4o")
predictor = Predict(sig, provider)

# Use it
result = predictor(
    question="What is the capital?",
    context="France is a country in Europe. Paris is its capital."
)
print(result["answer"])  # "Paris"
```

## Signatures

### Basic Signature

```python
from rlm_toolkit.optimize import Signature

# Q&A signature
qa_sig = Signature(
    inputs=["question"],
    outputs=["answer"],
    instructions="Answer the question accurately"
)

# Classification signature
classify_sig = Signature(
    inputs=["text"],
    outputs=["category", "confidence"],
    instructions="Classify text into categories: tech, sports, politics"
)
```

### Factory Functions

```python
from rlm_toolkit.optimize import (
    create_qa_signature,
    create_summarize_signature,
    create_classify_signature
)

# Pre-built signatures
qa = create_qa_signature()
summarize = create_summarize_signature(max_words=100)
classify = create_classify_signature(categories=["positive", "negative", "neutral"])
```

## Modules

### Predict

Simple single-step prediction:

```python
from rlm_toolkit.optimize import Predict

predictor = Predict(signature, provider)
result = predictor(question="What is 2+2?")
```

### ChainOfThought

Step-by-step reasoning:

```python
from rlm_toolkit.optimize import ChainOfThought

cot = ChainOfThought(signature, provider)
result = cot(question="What is 15% of 80?")

print(result["reasoning"])  # Step-by-step explanation
print(result["answer"])     # "12"
```

### SelfRefine

Iterative self-improvement:

```python
from rlm_toolkit.optimize import SelfRefine

refiner = SelfRefine(
    signature, 
    provider,
    max_iterations=3,
    stop_condition=lambda r: r["confidence"] > 0.9
)

result = refiner(question="Complex reasoning task...")
print(f"Iterations: {result['iterations']}")
print(f"Final answer: {result['answer']}")
```

## Optimizers

### BootstrapFewShot

Automatically select best few-shot examples:

```python
from rlm_toolkit.optimize import Predict, BootstrapFewShot, Example

# Training examples
trainset = [
    Example(question="Capital of France?", answer="Paris"),
    Example(question="Capital of Japan?", answer="Tokyo"),
    Example(question="Capital of Brazil?", answer="Brasília"),
    # ... more examples
]

# Metric function
def exact_match(prediction, ground_truth):
    return prediction["answer"].lower() == ground_truth["answer"].lower()

# Optimize
optimizer = BootstrapFewShot(metric=exact_match, num_candidates=10)
optimized_predictor = optimizer.compile(
    Predict(signature, provider),
    trainset=trainset
)

# Now uses best few-shot examples automatically
result = optimized_predictor(question="Capital of Germany?")
```

### PromptOptimizer

Optimize prompt instructions:

```python
from rlm_toolkit.optimize import PromptOptimizer

optimizer = PromptOptimizer(
    metric=exact_match,
    num_trials=20,
    temperature=0.7
)

# Find best instructions
optimized = optimizer.optimize(
    module=Predict(signature, provider),
    trainset=trainset,
    valset=valset
)

print(f"Best instructions: {optimized.signature.instructions}")
print(f"Validation accuracy: {optimized.val_score:.2%}")
```

## Real-World Examples

### Example 1: Customer Support Classifier

```python
from rlm_toolkit.optimize import Signature, ChainOfThought, BootstrapFewShot

# Define task
sig = Signature(
    inputs=["ticket_text"],
    outputs=["category", "priority", "suggested_action"],
    instructions="Classify support ticket and suggest action"
)

# Training data
trainset = [
    Example(
        ticket_text="My order hasn't arrived",
        category="shipping",
        priority="high", 
        suggested_action="Check tracking, offer refund if >7 days"
    ),
    # ... 50 more examples
]

# Optimize
classifier = ChainOfThought(sig, provider)
optimizer = BootstrapFewShot(metric=category_match, num_candidates=5)
optimized = optimizer.compile(classifier, trainset=trainset)

# Production use
result = optimized(ticket_text="Where is my package?")
print(f"Category: {result['category']}")
print(f"Priority: {result['priority']}")
print(f"Action: {result['suggested_action']}")
```

### Example 2: Code Review Assistant

```python
sig = Signature(
    inputs=["code", "language"],
    outputs=["issues", "suggestions", "security_concerns"],
    instructions="Review code for bugs, style, and security"
)

reviewer = SelfRefine(sig, provider, max_iterations=2)

result = reviewer(
    code="""
def login(user, password):
    query = f"SELECT * FROM users WHERE user='{user}'"
    return db.execute(query)
""",
    language="python"
)

print("Security concerns:", result["security_concerns"])
# ["SQL injection vulnerability in query construction"]
```

### Example 3: Multi-Step Research

```python
from rlm_toolkit.optimize import ChainOfThought

# Research signature with reasoning
sig = Signature(
    inputs=["topic", "sources"],
    outputs=["summary", "key_findings", "confidence"],
    instructions="Analyze sources and extract key findings"
)

researcher = ChainOfThought(sig, provider)

result = researcher(
    topic="Climate change impact on agriculture",
    sources=[doc1, doc2, doc3]
)

print(f"Confidence: {result['confidence']}")
print(f"Key findings: {result['key_findings']}")
```

## Best Practices

| Practice | Benefit |
|----------|---------|
| Start with Predict | Simple baseline first |
| Add CoT for reasoning | Better accuracy on complex tasks |
| Use 20+ training examples | Reliable optimization |
| Validate on held-out set | Avoid overfitting |
| Monitor in production | Detect prompt drift |

## Related

- [Self-Evolving LLMs](self-evolving.md)
- [Tutorial: First App](../tutorials/01-first-app.md)
- [Observability](observability.md)
