# ML Architecture Security

> **Подмодуль (ML Fundamentals): Architecture Deep Dive**

---

## Обзор

Понимание архитектуры модели необходимо для security analysis. Этот подмодуль покрывает внутренние компоненты нейронных сетей и transformers с фокусом на безопасность.

---

## Топики

| Топик | Security Relevance |
|-------|-------------------|
| **Attention Mechanisms** | Где происходит context mixing |
| **Tokenization** | Input preprocessing attacks |
| **Embeddings** | Semantic space vulnerabilities |
| **Layers** | Gradient-based attacks |

---

## Уроки

### [01. Attention Mechanisms](01-attention.md)
**Время:** 40 минут | **Сложность:** Intermediate

Как transformers обрабатывают context:
- Self-attention механика
- Multi-head attention
- Attention visualization
- Exploitation patterns

### [02. Tokenization](02-tokenization.md)
**Время:** 35 минут | **Сложность:** Intermediate

Text-to-token конверсия:
- BPE, WordPiece, SentencePiece
- Token boundary attacks
- Glitch tokens
- Evasion techniques

### [03. Embeddings](03-embeddings.md)
**Время:** 35 минут | **Сложность:** Intermediate

Semantic representations:
- Embedding spaces
- Similarity attacks
- Adversarial embeddings
- Defense через embeddings

---

## Ключевые insights

### Security на каждом Layer

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

## Навигация

| Предыдущий | Текущий | Следующий |
|------------|---------|-----------|
| [Basics](../01-basics/) | **Architecture** | [Transformers](../03-transformers/) |

---

*AI Security Academy | ML Fundamentals Architecture*
