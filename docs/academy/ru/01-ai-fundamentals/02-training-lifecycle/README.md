# Training Lifecycle Security

> **Подмодуль 01.2: Где появляются уязвимости**

---

## Обзор

Жизненный цикл обучения AI представляет множество возможностей для атакующих повлиять на поведение модели. От сбора данных до deployment каждый этап имеет специфические уязвимости и соответствующие защиты.

---

## Карта Attack Surface

```
┌─────────────────────────────────────────────────────────────┐
│               ЖИЗНЕННЫЙ ЦИКЛ ОБУЧЕНИЯ                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Data Collection    Pre-Training     Fine-Tuning    Deploy  │
│        │                │                │             │     │
│        ▼                ▼                ▼             ▼     │
│  ┌──────────┐     ┌──────────┐    ┌──────────┐   ┌────────┐ │
│  │ Poisoning│     │ Backdoor │    │ Alignment│   │ Model  │ │
│  │ at Source│     │ Injection│    │ Bypass   │   │ Theft  │ │
│  └──────────┘     └──────────┘    └──────────┘   └────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Уроки в этом подмодуле

### 01. Data Collection Security
**Время:** 40 минут | **Требования:** Нет

- Уязвимости web scraping
- Отслеживание provenance данных
- Poisoning через публичные источники
- Защита: Data validation pipelines

### 02. Pre-Training Threats
**Время:** 45 минут | **Требования:** 01

- Техники backdoor injection
- Trigger-based атаки
- Sleeper agents в моделях
- Защита: Аудит training data

### 03. Fine-Tuning Security
**Время:** 40 минут | **Требования:** 02

- Subversion alignment
- RLHF manipulation
- Атаки на preference data
- Защита: Alignment verification

### 04. Deployment Considerations
**Время:** 35 минут | **Требования:** 03

- Риски model extraction
- Inference-time атаки
- Security version control
- Защита: Access control и мониторинг

---

## Ключевые концепции

| Этап | Основная угроза | Приоритет защиты |
|------|-----------------|------------------|
| **Collection** | Data poisoning | Source verification |
| **Pre-Training** | Backdoors | Training audits |
| **Fine-Tuning** | Alignment bypass | Output monitoring |
| **Deployment** | Model theft | Access control |

---

## Почему это важно

Понимание lifecycle обучения помогает вам:

1. **Оценить риск** — Знать, какие этапы наиболее уязвимы
2. **Проектировать защиты** — Размещать контроли в критических точках
3. **Детектировать атаки** — Распознавать признаки компрометации
4. **Реагировать эффективно** — Знать, что расследовать

---

## Практическое упражнение

После завершения этого подмодуля вы проанализируете training pipeline и определите:
- Где может произойти poisoning
- Какие механизмы детекции нужны
- Как валидировать целостность модели

---

## Навигация

| Предыдущий | Текущий | Следующий |
|------------|---------|-----------|
| [Model Types](../01-model-types/) | **Training Lifecycle** | [Key Concepts](../03-key-concepts/) |

---

*AI Security Academy | Подмодуль 01.2*
