# Guardrails

> **Подмодуль 05.2: Активные контроли защиты**

---

## Обзор

Guardrails — активные контроли, которые обеспечивают соблюдение политик безопасности в runtime. Охватывает input, output и system-level guardrails.

---

## Типы Guardrails

| Тип | Позиция | Назначение |
|-----|---------|------------|
| **Input** | До LLM | Блокировка вредоносных запросов |
| **Output** | После LLM | Блокировка опасных ответов |
| **System** | Всегда | Обеспечение инвариантов |
| **Action** | Tool-level | Контроль действий агента |

---

## Уроки

### 01. Input Guardrails
**Время:** 40 минут | **Сложность:** Средняя

Фильтрация входящих запросов:
- Content policy enforcement
- Injection detection integration
- Topic restrictions
- Rate limiting

### 02. Output Guardrails
**Время:** 40 минут | **Сложность:** Средняя

Фильтрация ответов модели:
- Harmful content blocking
- PII/credential redaction
- Policy compliance
- Response modification

### 03. System Guardrails
**Время:** 35 минут | **Сложность:** Средняя

Инфраструктурные контроли:
- Token budget
- Timeout
- Resource quotas
- Circuit breakers

---

## Архитектура

```
User Input
    │
    ▼
┌────────────────┐
│ INPUT GUARDS   │ ← Block/modify до LLM
└────────────────┘
    │
    ▼
┌────────────────┐
│     LLM        │
└────────────────┘
    │
    ▼
┌────────────────┐
│ OUTPUT GUARDS  │ ← Block/modify после LLM
└────────────────┘
    │
    ▼
Safe Response
```

---

## Навигация

| Предыдущий | Текущий | Следующий |
|------------|---------|-----------|
| [Детекция](../01-detection/) | **Guardrails** | [Response](../02-response/) |

---

*AI Security Academy | Подмодуль 05.2*
