# ML Architecture Security

> **Submodule (ML Fundamentals): Architecture Deep Dive**

---

## Overview

Understanding model architecture is essential for security analysis. This submodule covers the internal components of neural networks and transformers with a security focus.

---

## Topics

| Topic | Security Relevance |
|-------|-------------------|
| **Attention Mechanisms** | Where context mixing occurs |
| **Tokenization** | Input preprocessing attacks |
| **Embeddings** | Semantic space vulnerabilities |
| **Layers** | Gradient-based attacks |

---

## Lessons

### [01. Attention Mechanisms](01-attention.md)
**Time:** 40 minutes | **Difficulty:** Intermediate

How transformers process context:
- Self-attention mechanics
- Multi-head attention
- Attention visualization
- Exploitation patterns

### [02. Tokenization](02-tokenization.md)
**Time:** 35 minutes | **Difficulty:** Intermediate

Text-to-token conversion:
- BPE, WordPiece, SentencePiece
- Token boundary attacks
- Glitch tokens
- Evasion techniques

### [03. Embeddings](03-embeddings.md)
**Time:** 35 minutes | **Difficulty:** Intermediate

Semantic representations:
- Embedding spaces
- Similarity attacks
- Adversarial embeddings
- Defense via embeddings

---

## Key Insights

### Security at Each Layer

```
Input Text
    │
    ▼ Tokenizer (boundary attacks)
Tokens
    │
    ▼ Embeddings (semantic attacks)
Vectors
    │
    ▼ Attention (context mixing)
Representations
    │
    ▼ Output layers
Response
```

---

## Navigation

| Previous | Current | Next |
|----------|---------|------|
| [Basics](../01-basics/) | **Architecture** | [Transformers](../03-transformers/) |

---

*AI Security Academy | ML Fundamentals Architecture*
