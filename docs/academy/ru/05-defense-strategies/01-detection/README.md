# Detection Methods

> **Подмодуль 05.1: Обнаружение атак до их успеха**

---

## Обзор

Detection — первая линия защиты. Этот подмодуль покрывает спектр техник детекции, от простого pattern matching до продвинутого topological analysis, обучая вас когда использовать каждый подход.

---

## Спектр детекции

| Метод | Скорость | Точность | Лучше для |
|-------|----------|----------|-----------|
| **Exact match** | Быстрейший | Низкая | Known payloads |
| **Pattern (regex)** | Быстрый | Средняя | Known patterns |
| **Semantic** | Средний | Высокая | Paraphrased attacks |
| **Topological** | Медленный | Очень высокая | Novel attacks |
| **ML-based** | Средний | Высокая | Complex patterns |

---

## Уроки

### [01. Pattern Matching Detection](01-pattern-matching.md)
**Время:** 35 минут | **Сложность:** ����������-�������

Быстрая, rule-based детекция:
- Дизайн regex patterns
- Иерархическое matching
- Evasion-resistant patterns
- Оптимизация производительности

### 02. Semantic Analysis
**Время:** 40 минут | **Сложность:** �������

Meaning-based детекция:
- Embedding similarity
- Intent classification
- Anomaly detection
- Hybrid подходы

### 03. Topological Detection
**Время:** 45 минут | **Сложность:** �����������

Структурный анализ:
- Persistent homology
- Attack signatures
- Embedding topology
- Novel attack detection

### 04. Ensemble Methods
**Время:** 40 минут | **Сложность:** �����������

Комбинирование методов детекции:
- Voting strategies
- Confidence weighting
- Cascade architectures
- Latency optimization

---

## Detection Pipeline

```
Input Text
    │
    ▼
[ Fast Blocklist ] ──blocked──► REJECT
    │ pass
    ▼
[ Pattern Matching ] ──high confidence──► REJECT
    │ uncertain
    ▼
[ Semantic Analysis ] ──attack likely──► REJECT
    │ uncertain
    ▼
[ Full Analysis ] ──confirmed attack──► REJECT
    │ clean
    ▼
ALLOW
```

---

## Ключевые insights

### Speed vs Accuracy Tradeoff

- **Production** — Приоритет скорости, принять некоторые false negatives
- **Security-critical** — Приоритет точности, принять latency
- **Balanced** — Multi-stage pipeline с early exit

### Частые ошибки

| Ошибка | Последствие | Fix |
|--------|-------------|-----|
| Только regex | Лёгкий обход | Добавить semantic layer |
| Без нормализации | Homoglyph bypass | Normalize before match |
| Flat architecture | Медленно на scale | Использовать hierarchical |

---

## Навигация

| Предыдущий | Текущий | Следующий |
|------------|---------|-----------|
| [Обзор модуля](../README.md) | **Detection** | [Guardrails](../02-guardrails/) |

---

*AI Security Academy | Подмодуль 05.1*
