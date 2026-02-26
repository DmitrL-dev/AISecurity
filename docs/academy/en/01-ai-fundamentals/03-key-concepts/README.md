# Key Concepts in AI Security

> **Submodule 01.3: Essential Building Blocks**

---

## Overview

Certain concepts appear repeatedly throughout AI security. This submodule provides deep dives into these foundational elements, explaining both how they work and why they matter for security.

---

## Core Concepts

| Concept | What It Is | Security Relevance |
|---------|------------|-------------------|
| **Tokenization** | Converting text to numbers | Attack pattern detection, evasion |
| **Embeddings** | Semantic representations | Similarity detection, anomaly finding |
| **Attention** | How models focus | Understanding model behavior |
| **Context Windows** | Memory limits | Injection persistence, DoS |

---

## Lessons in This Submodule

### [01. Tokenization and Embeddings](01-tokenization-embeddings.md)
**Time:** 35 minutes | **Prerequisites:** Module 01.1

Understanding how text becomes numbers and meaning:

- **Tokenization Algorithms** - BPE, WordPiece, SentencePiece
- **Security Implications**
  - Token boundary attacks
  - Homoglyph evasion
  - Glitch token exploitation
- **Embedding Security**
  - Semantic similarity detection
  - Anomaly detection in embedding space
  - Adversarial embeddings

### 02. Context Windows
**Time:** 30 minutes | **Prerequisites:** 01

How context limits affect security:

- **Window Size Implications**
  - Attack persistence across windows
  - Memory exhaustion attacks
  - Instruction anchoring
- **Defense Strategies**
  - Context partitioning
  - Priority-based truncation

### 03. Temperature and Sampling
**Time:** 25 minutes | **Prerequisites:** None

Output randomness and security:

- **Temperature Effects**
  - Deterministic vs. stochastic outputs
  - Reproducibility for forensics
- **Sampling Strategies**
  - Top-k, top-p implications
  - Attack repeatability

---

## Why These Concepts Matter

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

## Key Insights

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

## Practical Applications

After this submodule, you'll be able to:

1. **Build token-aware detectors** that can't be evaded by spacing tricks
2. **Implement semantic detection** that catches paraphrased attacks
3. **Understand model behavior** through attention analysis
4. **Design context-aware defenses** that handle long conversations

---

## Hands-On Exercises

- Analyze how different inputs tokenize
- Build an embedding-based attack detector
- Experiment with context window effects

---

## Navigation

| Previous | Current | Next |
|----------|---------|------|
| [Training Lifecycle](../02-training-lifecycle/) | **Key Concepts** | [Module 02: Threats](../../02-threat-landscape/) |

---

*AI Security Academy | Submodule 01.3*
