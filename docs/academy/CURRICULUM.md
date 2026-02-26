# AI Security Academy — Полная программа (CURRICULUM)

> **Версия:** 1.0.0  
> **Дата:** Январь 2026  
> **Всего уроков:** 300+  
> **Всего лабораторных:** 100+

---

## Обзор треков

| # | Track | Уроков | Лаб | Уровень |
|---|-------|--------|-----|---------|
| 00 | Introduction | 4 | - | All |
| 01 | AI Fundamentals | 26 | - | Beginner |
| 02 | Threat Landscape | 43 | - | Beginner+ |
| 03 | Attack Vectors | 53 | 20 | Intermediate |
| 04 | Agentic Security | 46 | 10 | Intermediate |
| 05 | Defense Strategies | 100 | 20 | Intermediate+ |
| 06 | Advanced Detection | 42 | 10 | Advanced |
| 07 | Governance | 36 | - | Advanced |
| 08 | Labs | - | 100 | All |

---

## Track 00: Introduction

### 00.1 Добро пожаловать
- 00-welcome.md — Введение в Academy
- 01-how-to-use.md — Как пользоваться курсом
- 02-learning-paths.md — Пути обучения
- 03-prerequisites.md — Предварительные требования

---

## Track 01: AI Fundamentals

### 01.1 Типы моделей (10 уроков)
- 01-transformers.md — Transformer архитектура
- 02-encoder-only.md — BERT, RoBERTa
- 03-decoder-only.md — GPT, LLaMA, Claude
- 04-encoder-decoder.md — T5, BART
- 05-vision-transformers.md — ViT
- 06-multimodal.md — GPT-4V, Gemini, Claude Vision
- 07-mixture-of-experts.md — Mixtral, Switch
- 08-state-space.md — Mamba, S4
- 09-diffusion.md — Stable Diffusion, DALL-E
- 10-audio-models.md — Whisper, AudioPalm

### 01.2 Архитектурные компоненты (8 уроков)
- 01-attention.md — Attention mechanisms
- 02-positional-encoding.md — Positional encoding
- 03-tokenization.md — BPE, WordPiece, SentencePiece
- 04-embeddings.md — Token и sentence embeddings
- 05-context-windows.md — Context windows
- 06-kv-cache.md — KV cache и оптимизации
- 07-quantization.md — INT8, INT4, GPTQ
- 08-adapters.md — LoRA, адаптеры

### 01.3 Inference (4 урока)
- 01-batching.md — Batching strategies
- 02-speculative-decoding.md — Speculative decoding
- 03-parallelism.md — Tensor parallelism
- 04-serving.md — Model serving (vLLM, TGI)

### 01.4 Training (4 урока)
- 01-pretraining.md — Pre-training
- 02-instruction-tuning.md — Instruction tuning
- 03-rlhf.md — RLHF/DPO
- 04-synthetic-data.md — Synthetic data training

---

## Track 02: Threat Landscape

### 02.1 OWASP LLM Top 10 (10 уроков)
- LLM01-prompt-injection.md
- LLM02-sensitive-disclosure.md
- LLM03-supply-chain.md
- LLM04-data-model-poisoning.md
- LLM05-improper-output.md
- LLM06-excessive-agency.md
- LLM07-system-prompt-leakage.md
- LLM08-vector-embeddings.md
- LLM09-misinformation.md
- LLM10-unbounded-consumption.md

### 02.2 OWASP ASI Top 10 (10 уроков)
- ASI01-agentic-injection.md
- ASI02-privilege-escalation.md
- ASI03-identity-spoofing.md
- ASI04-supply-chain.md
- ASI05-memory-threats.md
- ASI06-goal-drift.md
- ASI07-communication-threats.md
- ASI08-resource-threats.md
- ASI09-trust-exploitation.md
- ASI10-human-threats.md

### 02.3 Threat Actors (5 уроков)
### 02.4 Attack Surfaces (6 уроков)
### 02.5 Historical Incidents (6 уроков)
### 02.6 Emerging Threats (6 уроков)

---

## Track 03: Attack Vectors

### 03.1 Prompt Injection (8 техник)
### 03.2 Jailbreaks (17 техник)
### 03.3 Data Poisoning (7 техник)
### 03.4 Model Attacks (7 техник)
### 03.5 Infrastructure Attacks (7 техник)
### 03.6 Agentic Attacks (7 техник)

---

## Track 04: Agentic Security

### 04.1 Agent Architectures (7 уроков)
### 04.2 Protocols (7 уроков)
### 04.3 Trust & Authorization (7 уроков)
### 04.4 Tool Security (7 уроков)
### 04.5 Memory Security (7 уроков)
### 04.6 Multi-Agent Threats (6 уроков)
### 04.7 Human-Agent Interaction (5 уроков)

---

## Track 05: Defense Strategies

### 05.1 Detection (30 стратегий)
### 05.2 Prevention (30 стратегий)
### 05.3 Response (20 стратегий)
### 05.4 Recovery (20 стратегий)

---

## Track 06: Advanced Detection

### 06.1 TDA (10 уроков)
### 06.2 Geometric Methods (7 уроков)
### 06.3 Information Geometry (6 уроков)
### 06.4 Dynamical Systems (6 уроков)
### 06.5 Category Theory (6 уроков)
### 06.6 Novel Methods (7 уроков)

---

## Track 07: Governance

### 07.1 SENTINEL Framework (8 уроков)
### 07.2 International Standards (5 уроков)
### 07.3 Regional Frameworks (5 уроков)
### 07.4 Industry Standards (5 уроков)
### 07.5 Organizational Governance (6 уроков)
### 07.6 Technical Controls (7 уроков)

---

## Track 08: Labs

### 08.1 STRIKE Red Team (40 лабораторных)
### 08.2 SENTINEL Blue Team (40 лабораторных)
### 08.3 Purple Team (20 лабораторных)
### 08.4 CTF Challenges (20 заданий)

---

## Сертификации

| Уровень | Треки | Вопросов | Проходной |
|---------|-------|----------|-----------|
| Beginner | 00-02 | 50 | 70% |
| Intermediate | 00-05 | 75 | 75% |
| Advanced | 00-07 | 100 | 80% |
| Expert | 00-08 + Capstone | 100 | 85% |

---

*Программа версии 1.0.0 — Январь 2026*
