# AI Fundamentals

> **Модуль 01: Понимание основ**

---

## Обзор

Прежде чем защищать AI системы, вы должны понимать, как они работают. Этот модуль охватывает архитектуру, процессы обучения и ключевые концепции, лежащие в основе современных AI систем — с security линзой на протяжении всего курса.

---

## Что вы узнаете

| Тема | Релевантность для безопасности |
|------|-------------------------------|
| **Model Architectures** | Attack surfaces различаются по типу модели |
| **Training Lifecycle** | Где происходят poisoning и supply chain атаки |
| **Key Concepts** | Tokenization, embeddings и их уязвимости |

---

## Подмодули

### [01. Model Types](01-model-types/)
Понимание различных AI архитектур и их security implications:
- Large Language Models (LLMs)
- Vision-Language Models
- Diffusion Models
- State Space Models
- Multimodal Systems

### [02. Training Lifecycle](02-training-lifecycle/)
Узнайте, где уязвимости появляются во время обучения:
- Сбор и курирование данных
- Pre-training и fine-tuning
- Техники alignment (RLHF, DPO)
- Соображения по deployment

### [03. Key Concepts](03-key-concepts/)
Освойте фундаментальные концепции:
- Tokenization и её security implications
- Embeddings и семантические пространства
- Механизмы attention
- Context windows

---

## Цели обучения

К концу этого модуля вы сможете:

1. **Объяснять** как различные архитектуры моделей обрабатывают ввод
2. **Идентифицировать** attack surfaces на каждом этапе AI lifecycle
3. **Понимать** как tokenization влияет на меры безопасности
4. **Распознавать** где существуют trust boundaries в AI системах

---

## Ключевые уроки

| Урок | Время | Описание |
|------|-------|----------|
| Neural Networks | 35 мин | Архитектура и уязвимости |
| Training Security | 40 мин | Data poisoning и backdoors |
| Tokenization | 35 мин | Token-level атаки и защиты |
| Embeddings | 35 мин | Семантический анализ для безопасности |
| Attention | 40 мин | Как transformers обрабатывают информацию |
| State Space Models | 35 мин | SSM-специфичные security concerns |

---

## Предварительные требования

- Базовое понимание machine learning (что означает training)
- Опыт программирования на Python
- Предварительные знания по безопасности не требуются

---

## Связь с Security

Понимание этих основ поможет вам:

```
Model Architecture → Понять, что может быть атаковано
        ↓
Training Process → Знать, где происходит poisoning
        ↓
Tokenization → Строить лучшие input filters
        ↓
Embeddings → Реализовать semantic detection
```

---

## Практические применения

После этого модуля вы поймёте:

- Почему определённые атаки работают против LLM, но не других типов моделей
- Как качество training data влияет на security модели
- Почему tokenization важна для prompt injection detection
- Как embeddings включают semantic attack detection

---

## Навигация

**Начните здесь:** [Model Types →](01-model-types/)

| Предыдущий | Текущий | Следующий |
|------------|---------|-----------|
| [Introduction](../00-introduction/) | **AI Fundamentals** | [Threat Landscape](../02-threat-landscape/) |

---

*AI Security Academy | Модуль 01*
