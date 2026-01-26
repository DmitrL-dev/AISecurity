# Model-Level Attacks

> **Submodule 03.3: Attacks on the Model Itself**

---

## Обзор

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

### 01. Data Extraction
**Время:** 40 minutes | **Сложность:** Продвинутый

Recovering training data:
- Memorization exploitation
- Prefix attacks
- Verbatim extraction
- PII and credential leakage

### 02. Membership Inference
**Время:** 40 minutes | **Сложность:** Средний

Determining training data membership:
- Statistical analysis techniques
- Confidence score analysis
- Shadow model training
- Privacy implications

### 03. Adversarial Examples
**Время:** 45 minutes | **Сложность:** Средний

Crafting inputs that fool models:
- Gradient-based attacks
- Transfer attacks
- Black-box techniques
- Defense mechanisms

---

## Attack Surface

```
Model API
    в”‚
    в”њв”Ђв”Ђ Logits/Probabilities в†’ Membership Inference
    в”њв”Ђв”Ђ Embeddings в†’ Adversarial Examples  
    в”њв”Ђв”Ђ Generated Text в†’ Data Extraction
    в””в”Ђв”Ђ Query Access в†’ Model Extraction
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

## Навигация

| Previous | Current | Next |
|----------|---------|------|
| [Jailbreaking](../02-jailbreaks/) | **Model-Level** | [Prompt-Level](../04-prompt-level/) |

---

*AI Security Academy | Submodule 03.3*
