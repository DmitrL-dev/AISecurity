# AI Fundamentals

> **Module 01: Understanding the Foundation**

---

## Overview

Before defending AI systems, you must understand how they work. This module covers the architecture, training processes, and key concepts that underpin modern AI systems—with a security lens throughout.

---

## What You'll Learn

| Topic | Security Relevance |
|-------|-------------------|
| **Model Architectures** | Attack surfaces differ by model type |
| **Training Lifecycle** | Where poisoning and supply chain attacks occur |
| **Key Concepts** | Tokenization, embeddings, and their vulnerabilities |

---

## Submodules

### [01. Model Types](01-model-types/)
Understand different AI architectures and their security implications:
- Large Language Models (LLMs)
- Vision-Language Models
- Diffusion Models
- State Space Models
- Multimodal Systems

### [02. Training Lifecycle](02-training-lifecycle/)
Learn where vulnerabilities enter during training:
- Data collection and curation
- Pre-training and fine-tuning
- Alignment techniques (RLHF, DPO)
- Deployment considerations

### [03. Key Concepts](03-key-concepts/)
Master foundational concepts:
- Tokenization and its security implications
- Embeddings and semantic spaces
- Attention mechanisms
- Context windows

---

## Learning Objectives

By the end of this module, you will be able to:

1. **Explain** how different model architectures process input
2. **Identify** attack surfaces at each stage of the AI lifecycle
3. **Understand** how tokenization affects security measures
4. **Recognize** where trust boundaries exist in AI systems

---

## Key Lessons

| Lesson | Time | Description |
|--------|------|-------------|
| Neural Networks | 35 min | Architecture and vulnerabilities |
| Training Security | 40 min | Data poisoning and backdoors |
| Tokenization | 35 min | Token-level attacks and defenses |
| Embeddings | 35 min | Semantic analysis for security |
| Attention | 40 min | How transformers process information |
| State Space Models | 35 min | SSM-specific security concerns |

---

## Prerequisites

- Basic understanding of machine learning (what training means)
- Python programming experience
- No prior security knowledge required

---

## How Security Relates

Understanding these fundamentals helps you:

```
Model Architecture → Understand what can be attacked
        ↓
Training Process → Know where poisoning occurs
        ↓
Tokenization → Build better input filters
        ↓
Embeddings → Implement semantic detection
```

---

## Practical Applications

After this module, you'll understand:

- Why certain attacks work against LLMs but not other model types
- How training data quality affects model security
- Why tokenization matters for prompt injection detection
- How embeddings enable semantic attack detection

---

## Navigation

**Start here:** [Model Types →](01-model-types/)

| Previous | Current | Next |
|----------|---------|------|
| [Introduction](../00-introduction/) | **AI Fundamentals** | [Threat Landscape](../02-threat-landscape/) |

---

*AI Security Academy | Module 01*
