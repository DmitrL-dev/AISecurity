# Модуль 01.1: Типы моделей

> **Трек:** 01 — AI Fundamentals  
> **Уровень:** ����������  
> **Время:** ~5 часов  
> **Уроки:** 6

---

## Обзор модуля

Этот модуль охватывает основные архитектуры моделей машинного обучения, которые составляют основу современного AI. Понимание этих архитектур критично для понимания их уязвимостей и методов защиты.

---

## Уроки

| # | Урок | Время | Описание |
|---|------|-------|----------|
| 01 | [Transformer архитектура](01-transformers.md) | 60 мин | Self-attention, encoder-decoder, позиционное кодирование |
| 02 | [Encoder-Only модели](02-encoder-only.md) | 55 мин | BERT, RoBERTa, MLM, NSP, fine-tuning |
| 03 | [Decoder-Only модели](03-decoder-only.md) | 60 мин | GPT, LLaMA, Claude, Constitutional AI |
| 04 | [Encoder-Decoder модели](04-encoder-decoder.md) | 50 мин | T5, BART, cross-attention, seq2seq |
| 05 | [Vision Transformers](05-vision-transformers.md) | 45 мин | ViT, patches, DeiT, Swin |
| 06 | [Multimodal модели](06-multimodal.md) | 50 мин | CLIP, LLaVA, visual understanding |

---

## Цели обучения

После завершения этого модуля вы сможете:

- ✅ Объяснить архитектуру Transformer и механизм self-attention
- ✅ Различать encoder-only, decoder-only и encoder-decoder архитектуры
- ✅ Понимать pre-training и fine-tuning парадигмы
- ✅ Описать Vision Transformer и его применение к изображениям
- ✅ Объяснить multimodal модели и contrastive learning
- ✅ Связать архитектурные особенности с уязвимостями безопасности

---

## Связь с безопасностью

Каждый тип архитектуры имеет свои уникальные уязвимости:

| Архитектура | Ключевые уязвимости | SENTINEL Engines |
|-------------|---------------------|------------------|
| **Encoder-only** | Adversarial examples, backdoors | `EmbeddingShiftDetector` |
| **Decoder-only** | Prompt injection, jailbreaks | `PromptInjectionDetector` |
| **Encoder-Decoder** | Cross-attention manipulation | `CrossAttentionMonitor` |
| **Vision** | Adversarial patches | `PatchAnomalyScanner` |
| **Multimodal** | Visual prompt injection | `VisualPromptInjectionDetector` |

---

## Предварительные требования

- Базовое понимание машинного обучения
- Знакомство с Python и PyTorch (для практических заданий)
- Линейная алгебра (матричные операции)

---

## Практические навыки

После завершения модуля вы получите опыт работы с:

```python
# HuggingFace Transformers
from transformers import (
    BertModel,                    # Encoder-only
    GPT2Model,                    # Decoder-only
    T5ForConditionalGeneration,   # Encoder-Decoder
    ViTForImageClassification,    # Vision
    CLIPModel                     # Multimodal
)
```

---

## Следующий модуль

→ [Модуль 01.2: Жизненный цикл обучения](../02-training-lifecycle/README.md)

---

*AI Security Academy | Track 01: AI Fundamentals*
