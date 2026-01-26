# Архитектуры агентов

> **Подмодуль 04.1b: Понимание структуры агентных систем**

---

## Обзор

Понимание архитектуры агентов критично для их защиты. Этот подмодуль рассматривает основные паттерны построения агентов и их уязвимости.

---

## Типы архитектур

| Архитектура | Описание | Применение |
|-------------|----------|------------|
| **Single Agent** | Один LLM + инструменты | Простые задачи |
| **Multi-Agent** | Несколько специализированных | Сложные workflow |
| **Hierarchical** | Главный + подчинённые | Enterprise |
| **Swarm** | Децентрализованные | Research |

---

## Уроки

### 01. Single Agent архитектура
**Время:** 35 минут | **Сложность:** Средняя

Базовая структура:
- LLM core
- Tool registry
- Memory systems
- Security boundaries

### 02. Multi-Agent системы
**Время:** 40 минут | **Сложность:** Средняя-Высокая

Координация агентов:
- Communication protocols
- Trust relationships
- Isolation mechanisms
- Attack propagation

### 03. Enterprise patterns
**Время:** 45 минут | **Сложность:** Высокая

Корпоративные паттерны:
- Governance integration
- Audit logging
- Compliance requirements
- Scalability security

---

## Attack Surface

```
                    ┌─────────────┐
User Input ────────►│   Agent     │◄──── Malicious tool
                    │   (LLM)     │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         ┌────────┐   ┌────────┐   ┌────────┐
         │ Tool 1 │   │ Tool 2 │   │Memory  │
         └────────┘   └────────┘   └────────┘
              │            │            │
              ▼            ▼            ▼
         External       Database    Persistent
          API                         State
```

---

## Навигация

| Предыдущий | Текущий | Следующий |
|------------|---------|-----------|
| [Agent Loops](../01-agent-loops/) | **Архитектуры** | [Протоколы](../02-protocols/) |

---

*AI Security Academy | Подмодуль 04.1b*
