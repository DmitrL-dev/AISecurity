# Agent Loops

> **Подмодуль 04.1b: Безопасность Loop Patterns**

---

## Обзор

Agent loops (ReAct, plan-and-execute и др.) — ключевые паттерны в agentic AI. Этот подмодуль покрывает security considerations специфичные для итеративного выполнения агентов, включая loop control, state management и предотвращение эксплуатации.

---

## Loop Patterns

| Pattern | Структура | Основной риск |
|---------|-----------|---------------|
| **ReAct** | Thought-Action-Observation | Loop hijacking |
| **Plan-Execute** | Plan > Execute steps | Plan manipulation |
| **Reflection** | Execute > Evaluate > Adjust | Evaluation exploitation |
| **Autonomous** | Goal > Plan > Execute > Verify | Goal drift |

---

## Уроки

### 01. Loop Control Security
**Время:** 35 минут | **Сложность:** Средний

Контроль выполнения loop:
- Termination conditions и валидация
- Enforcement жёстких iteration limits
- Паттерны детекции stuck loops
- Стратегии resource capping

### 02. State Management
**Время:** 40 минут | **Сложность:** Средний-Продвинутый

Безопасность persistent state:
- Риски state persistence
- Cross-iteration information leakage
- Техники state sanitization
- Паттерны checkpoint security

### 03. Loop Exploitation
**Время:** 40 минут | **Сложность:** Продвинутый

Понимание loop атак:
- Паттерны infinite loop атак
- Техники progress manipulation
- Goal drift exploitation
- Атаки state corruption

### 04. Defensive Patterns
**Время:** 35 минут | **Сложность:** Средний

Построение secure loops:
- Watchdog implementations
- Progress verification
- Output monitoring
- Automatic intervention

---

## Ключевые контроли

| Контроль | Цель | Implementation |
|----------|------|----------------|
| **Iteration limits** | Prevent infinite loops | Hard cap, configurable |
| **Timeout enforcement** | Time-bound execution | Per-iteration + total |
| **State validation** | Check each iteration | Schema + semantic |
| **Output monitoring** | Track progression | Anomaly detection |
| **Resource limits** | Prevent DoS | Token/API budgets |

---

## Архитектура Loop Security

```
--------------------------------------------------------------¬
¦                    SECURE AGENT LOOP                         ¦
+-------------------------------------------------------------+
¦                                                              ¦
¦  -----------¬    -----------¬    -----------¬              ¦
¦  ¦  Input   ¦ > ¦  Process ¦ > ¦  Output  ¦              ¦
¦  ¦ Validate ¦    ¦ Execute  ¦    ¦ Validate ¦              ¦
¦  L-----------    L-----------    L-----------              ¦
¦       ¦              ¦               ¦                      ¦
¦       Ў              Ў               Ў                      ¦
¦  ------------------------------------------------------¬   ¦
¦  ¦              LOOP WATCHDOG                           ¦   ¦
¦  ¦  Iteration Count ¦ Time Elapsed ¦ Resources Used    ¦   ¦
¦  L------------------------------------------------------   ¦
¦                         ¦                                   ¦
¦                         Ў                                   ¦
¦                    [TERMINATE if limits exceeded]           ¦
¦                                                              ¦
L--------------------------------------------------------------
```

---

## Навигация

| Предыдущий | Текущий | Следующий |
|------------|---------|-----------|
| [Обзор модуля](../README.md) | **Agent Loops** | [Protocols](../02-protocols/) |

---

*AI Security Academy | Agent Loops*
