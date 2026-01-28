# Типы моделей

> **Подмодуль 01.1: Понимание архитектур AI моделей**

---

## Обзор

Разные типы AI моделей имеют разные характеристики безопасности. Понимание этих архитектур помогает идентифицировать attack surfaces и подходящие защиты для каждой.

---

## Категории моделей

| Категория | Примеры | Основное применение |
|-----------|---------|---------------------|
| **Language Models** | GPT, Claude, LLaMA | Генерация текста |
| **Vision-Language** | GPT-4V, Gemini Pro | Мультимодальные |
| **Diffusion Models** | Stable Diffusion, DALL-E | Генерация изображений |
| **State Space** | Mamba, S4 | Эффективные последовательности |
| **Encoder-Only** | BERT, RoBERTa | Классификация |

---

## Уроки

### 01. Large Language Models (LLMs)
**Время:** 40 минут | **Сложность:** Beginner-Intermediate

Основные transformer-based модели:
- Обзор архитектуры
- Механизмы attention
- Обработка промптов
- Последствия для безопасности

### 02. Vision-Language Models
**Время:** 35 минут | **Сложность:** Intermediate

Мультимодальные AI системы:
- Image + text обработка
- Cross-modal атаки
- Visual prompt injection
- Уникальные уязвимости

### 03. Diffusion Models
**Время:** 35 минут | **Сложность:** Intermediate

Системы генерации изображений:
- Denoising процесс
- Манипуляция промптами
- Обход content policy
- Watermarking

### [08. State Space Models](08-state-space.md)
**Время:** 35 минут | **Сложность:** Intermediate-Advanced

Эффективные sequence модели:
- State persistence
- Memory атаки
- SSM-специфичные защиты
- Сравнение с transformers

---

## Архитектура → Attack Surface

| Архитектура | Основная Attack Surface |
|-------------|------------------------|
| LLM (decoder-only) | System prompt, контекст |
| Vision-Language | Images + text комбинированно |
| Diffusion | Text prompts, negative prompts |
| State Space | State manipulation, память |
| Encoder-Only | Input perturbation |

---

## Ключевой инсайт

Архитектура модели определяет:
1. Какие входы она обрабатывает
2. Как поддерживает контекст
3. Какие выходы генерирует
4. Где существуют уязвимости

---

## Навигация

| Предыдущий | Текущий | Следующий |
|------------|---------|-----------|
| [Обзор модуля](../README.md) | **Типы моделей** | [Training Lifecycle](../02-training-lifecycle/) |

---

*AI Security Academy | Подмодуль 01.1*
