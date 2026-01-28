# Agentic AI Security

> **Модуль 04: Защита автономных AI-систем**

---

## Обзор

По мере эволюции AI-систем от простых чат-ботов к автономным агентам с инструментами, памятью и межагентной коммуникацией, ландшафт безопасности расширяется драматически. Этот модуль охватывает уникальные вызовы защиты agentic AI.

---

## Чем агенты отличаются

| Аспект | Traditional LLM | Agentic System |
|--------|----------------|----------------|
| **Actions** | Text generation | File/API/database access |
| **Persistence** | Stateless | Memory across sessions |
| **Autonomy** | Human-in-loop | Semi-autonomous decisions |
| **Scope** | Single model | Multi-agent orchestration |
| **Attack Surface** | Input/output | Entire tool ecosystem |

---

## Подмодули

### [01. Agent Architectures](01-architectures/)
Understanding agent design patterns:
- ReAct and tool-use patterns
- Multi-agent orchestration
- Memory and state management
- Security-first architecture design

### [02. Protocols](02-protocols/)
Securing inter-agent communication:
- MCP (Model Context Protocol)
- A2A (Agent-to-Agent)
- Function Calling security
- Trust delegation

### [03. Trust Boundaries](03-trust/)
Managing trust in agent systems:
- Boundary identification
- Privilege separation
- Capability-based security
- Trust verification

### [04. Tool Security](04-tools/)
Protecting tool usage:
- Tool definition security
- Argument validation
- Execution sandboxing
- Result sanitization

---

## Ключевые вызовы безопасности

```
More Capabilities = Larger Attack Surface + Higher Impact

Chatbot → Tool Use → Multi-Agent → Full Autonomy
   ↓         ↓           ↓             ↓
 Text     Actions     Lateral       Total
  Only    + Files     Movement      Control
```

---

## Attack → Defense Mapping

| Attack | Defense Layer |
|--------|---------------|
| Tool injection | Input validation |
| Privilege escalation | Capability limits |
| Cross-agent attacks | Trust boundaries |
| Memory poisoning | State validation |
| Goal hijacking | Objective monitoring |

---

## Путь обучения

### Рекомендуемый порядок
1. **Architectures** - Understand agent design
2. **Trust Boundaries** - Learn isolation principles
3. **Tool Security** - Protect tool usage
4. **Protocols** - Secure communication

### Hands-On Labs
Каждый подмодуль включает упражнения с использованием SENTINEL agent protection features.

---

## Пререквизиты

- Module 01: AI Fundamentals
- Module 02: Threat Landscape
- Module 03: Attack Vectors (at least 03.1)

---

## Навигация

| Previous | Current | Next |
|----------|---------|------|
| [Attack Vectors](../03-attack-vectors/) | **Agentic Security** | [Defense Strategies](../05-defense-strategies/) |

---

*AI Security Academy | Module 04*
