# Jailbreaking Techniques

> **Подмодуль 03.2: Обход мер безопасности**

---

## Обзор

Jailbreaking атаки направлены на обход safety measures и content policies, встроенных в AI системы. В отличие от prompt injection (который добавляет новые инструкции), jailbreaking убеждает модель игнорировать существующие ограничения.

---

## Категории Jailbreak

| Категория | Техника | Sophistication |
|-----------|---------|----------------|
| **Persona** | DAN, character roleplay | Low-Medium |
| **Gradual** | Crescendo, incremental escalation | Medium-High |
| **Flooding** | Many-shot, example normalization | Medium |
| **Format** | Virtualization, encoding | High |

---

## Уроки

### [01. DAN and Persona Attacks](01-dan.md)
**Время:** 35 минут | **Сложность:** Начинающий

Создание альтернативных personas для обхода ограничений:
- Эволюция DAN (Do Anything Now)
- Техники character roleplay
- Persistence personas между turn'ами
- Стратегии детекции и защиты

### [02. Crescendo Attack](02-crescendo.md)
**Время:** 40 минут | **Сложность:** Средний

Постепенная эскалация для обхода защит:
- Step-by-step нормализация
- Паттерны построения authority
- Эксплуатация refusal fatigue
- Multi-conversation persistence

### [03. Many-Shot Jailbreaking](03-many-shot.md)
**Время:** 40 минут | **Сложность:** Средний-Продвинутый

Использование примеров для нормализации запрещённых ответов:
- Эксплуатация in-context learning
- Pattern normalization
- Statistical bypasses
- Long-context vulnerabilities

### 04. Virtualization Attacks
**Время:** 35 минут | **Сложность:** Продвинутый

Создание вымышленных фреймов:
- Hypothetical scenarios
- Educational pretexts
- Размытие границ fiction/reality
- Nested context exploitation

---

## Эволюция Jailbreak

```
2023: Простые prompts ("Ignore rules")
        v
2024: Persona-based (DAN, characters)
        v
2025: Multi-turn gradual (Crescendo)
        v
2026: Statistical (Many-shot, context flooding)
```

---

## Ключевой Insight

Jailbreaks эксплуатируют напряжение между:
- **Helpfulness** — Модель хочет помочь
- **Safety** — Модель имеет ограничения
- **Role-play** — Модель может принимать personas

Атакующие используют helpfulness и role-play против safety.

---

## Приоритеты защиты

1. **Persona detection** — Идентифицикация jailbreak personas
2. **Escalation monitoring** — Отслеживание прогрессии запросов
3. **Output analysis** — Catch policy violations
4. **Context limits** — Предотвращение example flooding

---

## Навигация

| Предыдущий | Текущий | Следующий |
|------------|---------|-----------|
| [Prompt Injection](../01-prompt-injection/) | **Jailbreaking** | [Model-Level](../03-model-level/) |

---

*AI Security Academy | Подмодуль 03.2*
