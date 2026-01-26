# Agentic AI Security

> **Модуль 04: Безопасность автономных AI систем**

---

## Обзор

По мере того как AI системы эволюционируют от простых чатботов к автономным агентам с инструментами, памятью и multi-agent коммуникацией, ландшафт безопасности расширяется драматически. Этот модуль покрывает уникальные challenges безопасности agentic AI.

---

## Чем агенты отличаются

| Аспект | Традиционный LLM | Agentic System |
|--------|------------------|----------------|
| **Actions** | Генерация текста | Доступ к файлам/API/БД |
| **Persistence** | Stateless | Память между сессиями |
| **Autonomy** | Human-in-loop | Полуавтономные решения |
| **Scope** | Одна модель | Multi-agent orchestration |
| **Attack Surface** | Ввод/вывод | Вся tool ecosystem |

---

## Подмодули

### [01. Agent Architectures](01-architectures/)
Понимание архитектурных паттернов агентов:
- ReAct и tool-use паттерны
- Multi-agent orchestration
- Memory и state management
- Security-first architecture design

### [02. Protocols](02-protocols/)
Безопасность inter-agent коммуникации:
- MCP (Model Context Protocol)
- A2A (Agent-to-Agent)
- Function Calling security
- Trust delegation

### [03. Trust Boundaries](03-trust/)
Управление доверием в agent systems:
- Идентификация границ
- Разделение привилегий
- Capability-based security
- Верификация доверия

### [04. Tool Security](04-tools/)
Защита использования инструментов:
- Security tool definitions
- Валидация аргументов
- Execution sandboxing
- Санитизация результатов

---

## Ключевые Security Challenges

```
Больше Capabilities = Больше Attack Surface + Выше Impact

Chatbot → Tool Use → Multi-Agent → Full Autonomy
   ↓         ↓           ↓             ↓
 Только    Actions     Lateral       Total
  текст    + файлы     Movement      Control
```

---

## Attack → Defense Mapping

| Атака | Defense Layer |
|-------|---------------|
| Tool injection | Input validation |
| Privilege escalation | Capability limits |
| Cross-agent атаки | Trust boundaries |
| Memory poisoning | State validation |
| Goal hijacking | Objective monitoring |

---

## Путь обучения

### Рекомендованный порядок
1. **Architectures** — Понять дизайн агентов
2. **Trust Boundaries** — Изучить принципы изоляции
3. **Tool Security** — Защитить tool usage
4. **Protocols** — Обезопасить коммуникацию

### Hands-On Labs
Каждый подмодуль включает упражнения с использованием SENTINEL agent protection features.

---

## Предварительные требования

- Модуль 01: AI Fundamentals
- Модуль 02: Threat Landscape
- Модуль 03: Attack Vectors (минимум 03.1)

---

## Навигация

| Предыдущий | Текущий | Следующий |
|------------|---------|-----------|
| [Attack Vectors](../03-attack-vectors/) | **Agentic Security** | [Defense Strategies](../05-defense-strategies/) |

---

*AI Security Academy | Модуль 04*
