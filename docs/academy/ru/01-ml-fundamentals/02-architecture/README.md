# ML Architecture Security

> **Submodule (ML Fundamentals): Architecture Deep Dive**

---

## Обзор

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
**Время:** 40 minutes | **Сложность:** Средний

How transformers process context:
- Self-attention mechanics
- Multi-head attention
- Exploitation patterns

### [02. Tokenization](02-tokenization.md)
**Время:** 35 minutes | **Сложность:** Средний

Text-to-token conversion:
- BPE, WordPiece, SentencePiece
- Token boundary attacks
- Glitch tokens

### [03. Embeddings](03-embeddings.md)
**Время:** 35 minutes | **Сложность:** Средний

Semantic representations:
- Embedding spaces
- Adversarial embeddings
- Defense via embeddings

---

## Key Insights

### Security at Each Layer

```
Input Text
    в”‚
    в–ј Tokenizer (boundary attacks)
Tokens
    в”‚
    в–ј Embeddings (semantic attacks)
Vectors
    в”‚
    в–ј Attention (context mixing)
Representations
    в”‚
    в–ј Output layers
Response
```

---

## Навигация

| Previous | Current | Next |
|----------|---------|------|
| [Basics](../01-basics/) | **Architecture** | [Transformers](../03-transformers/) |

---

*AI Security Academy | ML Fundamentals Architecture*
