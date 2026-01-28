# Ключевые концепции AI Security

> **Подмодуль 01.3: Essential Building Blocks**

---

## Обзор

Определённые концепции появляются repeatedly throughout AI security. Этот подмодуль предоставляет deep dives в эти foundational elements, объясняя как они работают и почему важны для безопасности.

---

## Core Concepts

| Концепция | Что это | Security Relevance |
|-----------|---------|-------------------|
| **Tokenization** | Converting text to numbers | Attack pattern detection, evasion |
| **Embeddings** | Semantic representations | Similarity detection, anomaly finding |
| **Attention** | How models focus | Understanding model behavior |
| **Context Windows** | Memory limits | Injection persistence, DoS |

---

## Уроки в этом подмодуле

### [01. Tokenization and Embeddings](01-tokenization-embeddings.md)
**Время:** 35 минут | **Пререквизиты:** Module 01.1

Понимание как text становится numbers и meaning:

- **Tokenization Algorithms** — BPE, WordPiece, SentencePiece
- **Security Implications**
  - Token boundary attacks
  - Homoglyph evasion
  - Glitch token exploitation
- **Embedding Security**
  - Semantic similarity detection
  - Anomaly detection in embedding space
  - Adversarial embeddings

### 02. Context Windows
**Время:** 30 минут | **Пререквизиты:** 01

Как context limits влияют на security:

- **Window Size Implications**
  - Attack persistence across windows
  - Memory exhaustion attacks
  - Instruction anchoring
- **Defense Strategies**
  - Context partitioning
  - Priority-based truncation

### 03. Temperature and Sampling
**Время:** 25 минут | **Пререквизиты:** None

Output randomness и security:

- **Temperature Effects**
  - Deterministic vs. stochastic outputs
  - Reproducibility для forensics
- **Sampling Strategies**
  - Top-k, top-p implications
  - Attack repeatability

---

## Почему эти концепции важны

```
Tokenization → Understanding input processing
      ↓
Embeddings → Semantic attack detection
      ↓
Attention → Model behavior analysis
      ↓
Context → Attack persistence patterns
```

---

## Ключевые insights

### Tokenization Security

| Issue | Example | Impact |
|-------|---------|--------|
| Token splitting | "ig nore" vs "ignore" | Pattern evasion |
| Homoglyphs | Cyrillic "а" vs Latin "a" | Filter bypass |
| Glitch tokens | Anomalous embeddings | Unexpected behavior |

### Embedding Security

| Technique | Use Case |
|-----------|----------|
| Similarity search | Find paraphrased attacks |
| Anomaly detection | Identify novel attacks |
| Clustering | Group attack families |

---

## Практические применения

После этого подмодуля вы сможете:

1. **Build token-aware detectors** которые не обходятся spacing tricks
2. **Implement semantic detection** что ловит paraphrased attacks
3. **Understand model behavior** через attention analysis
4. **Design context-aware defenses** что handle long conversations

---

## Практические упражнения

- Analyze как разные inputs tokenize
- Build embedding-based attack detector
- Experiment с context window effects

---

## Навигация

| Предыдущий | Текущий | Следующий |
|------------|---------|-----------|
| [Training Lifecycle](../02-training-lifecycle/) | **Key Concepts** | [Module 02: Threats](../../02-threat-landscape/) |

---

*AI Security Academy | Подмодуль 01.3*
