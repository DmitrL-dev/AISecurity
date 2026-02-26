# Model Types

> **Submodule 01.1: Understanding AI Model Architectures**

---

## Overview

Different AI model types have different security characteristics. Understanding these architectures helps you identify attack surfaces and appropriate defenses for each.

---

## Model Categories

| Category | Examples | Primary Use |
|----------|----------|-------------|
| **Language Models** | GPT, Claude, LLaMA | Text generation |
| **Vision-Language** | GPT-4V, Gemini Pro | Multimodal |
| **Diffusion Models** | Stable Diffusion, DALL-E | Image generation |
| **State Space** | Mamba, S4 | Efficient sequences |
| **Encoder-Only** | BERT, RoBERTa | Classification |

---

## Lessons

### 01. Large Language Models (LLMs)
**Time:** 40 minutes | **Difficulty:** Beginner-Intermediate

Core transformer-based models:
- Architecture overview
- Attention mechanisms
- Prompt processing
- Security implications

### 02. Vision-Language Models
**Time:** 35 minutes | **Difficulty:** Intermediate

Multimodal AI systems:
- Image + text processing
- Cross-modal attacks
- Visual prompt injection
- Unique vulnerabilities

### 03. Diffusion Models
**Time:** 35 minutes | **Difficulty:** Intermediate

Image generation systems:
- Denoising process
- Prompt manipulation
- Content policy bypass
- Watermarking

### [08. State Space Models](08-state-space.md)
**Time:** 35 minutes | **Difficulty:** Intermediate-Advanced

Efficient sequence models:
- State persistence
- Memory attacks
- SSM-specific defenses
- Comparison with transformers

---

## Architecture → Attack Surface

| Architecture | Primary Attack Surface |
|--------------|----------------------|
| LLM (decoder-only) | System prompt, context |
| Vision-Language | Images + text combined |
| Diffusion | Text prompts, negative prompts |
| State Space | State manipulation, memory |
| Encoder-Only | Input perturbation |

---

## Key Insight

Model architecture determines:
1. What inputs it processes
2. How it maintains context
3. What outputs it generates
4. Where vulnerabilities exist

---

## Navigation

| Previous | Current | Next |
|----------|---------|------|
| [Module Overview](../README.md) | **Model Types** | [Training Lifecycle](../02-training-lifecycle/) |

---

*AI Security Academy | Submodule 01.1*
