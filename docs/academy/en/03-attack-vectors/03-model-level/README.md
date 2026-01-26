# Model-Level Attacks

> **Submodule 03.3: Attacks on the Model Itself**

---

## Overview

Model-level attacks target the ML model directly rather than exploiting application logic. These attacks require deeper technical knowledge but can have severe consequences including data extraction and model theft.

---

## Attack Categories

| Attack Type | Goal | Difficulty |
|-------------|------|------------|
| **Membership Inference** | Determine if data was in training | Medium |
| **Data Extraction** | Recover training data | Hard |
| **Adversarial Examples** | Fool model predictions | Medium |
| **Model Extraction** | Steal model weights | Very Hard |

---

## Lessons

### 01. Membership Inference
**Time:** 40 minutes | **Difficulty:** Intermediate

Determining training data membership:
- Statistical analysis techniques
- Confidence score analysis
- Shadow model training
- Privacy implications

### 02. Adversarial Examples
**Time:** 45 minutes | **Difficulty:** Intermediate

Crafting inputs that fool models:
- Gradient-based attacks
- Transfer attacks
- Black-box techniques
- Defense mechanisms

### 03. Data Extraction
**Time:** 45 minutes | **Difficulty:** Advanced

Recovering training data:
- Memorization exploitation
- Prefix attacks
- Verbatim extraction
- PII and credential leakage

### 04. Model Extraction
**Time:** 50 minutes | **Difficulty:** Expert

Stealing model functionality:
- Query-based extraction
- Distillation attacks
- Behavioral cloning
- Watermarking and detection

---

## Technical Requirements

These attacks often require:
- Access to model outputs (probabilities/logprobs)
- Understanding of model architecture
- Significant query volume
- Statistical analysis skills

---

## Attack Surface

```
Model API
    │
    ├── Logits/Probabilities → Membership Inference
    ├── Embeddings → Adversarial Examples  
    ├── Generated Text → Data Extraction
    └── Query Access → Model Extraction
```

---

## Real-World Impact

| Attack | Example Impact |
|--------|---------------|
| Membership Inference | Privacy violation, GDPR breach |
| Data Extraction | Credential leakage, PII exposure |
| Adversarial | Safety bypass, misclassification |
| Model Extraction | IP theft, competitive harm |

---

## Prerequisites

- Strong understanding of ML fundamentals
- Python programming skills
- Access to SENTINEL lab environment

---

## Navigation

| Previous | Current | Next |
|----------|---------|------|
| [Jailbreaking](../02-jailbreaks/) | **Model-Level** | [Prompt-Level](../04-prompt-level/) |

---

*AI Security Academy | Submodule 03.3*
