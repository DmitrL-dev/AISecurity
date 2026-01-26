# Protocol Security

> **Подмодуль 04.2: Безопасность Inter-Agent коммуникации**

---

## Обзор

Современные AI агенты коммуницируют через протоколы вроде MCP (Model Context Protocol), A2A (Agent-to-Agent) и function calling APIs. Каждый протокол имеет уникальные security considerations, которые должны быть поняты и адресованы.

---

## Ландшафт протоколов

| Протокол | Назначение | Основной риск |
|----------|------------|---------------|
| **MCP** | Доступ к tools/resources | Tool injection |
| **A2A** | Координация агентов | Trust delegation |
| **Function Calling** | OpenAI/Claude tools | Argument manipulation |
| **Custom APIs** | Proprietary integrations | Implementation flaws |

---

## Уроки

### [01. MCP Protocol Security](01-mcp.md)
**Время:** 45 минут | **Сложность:** �������-�����������

Безопасность Model Context Protocol:
- Валидация tool definitions
- Сканирование resource content
- Capability negotiation
- Transport security
- Интеграция SENTINEL

### 02. A2A Protocol Security
**Время:** 40 минут | **Сложность:** �����������

Agent-to-Agent коммуникация:
- Identity verification
- Trust chain management
- Message integrity
- Cross-agent authorization

### 03. Function Calling Security
**Время:** 40 минут | **Сложность:** �������

OpenAI/Anthropic function calling:
- Security function definitions
- Паттерны валидации аргументов
- Sandboxed execution
- Result sanitization

---

## Распространённые паттерны атак

```
Protocol Layer Attacks:

Tool Definition
      ├── Inject malicious descriptions
      └── Claim excessive capabilities

Message Content
      ├── Embed hidden instructions
      └── Exploit format parsing

Transport
      ├── Man-in-the-middle
      └── Session hijacking
```

---

## Defense Framework

| Layer | Control | Описание |
|-------|---------|----------|
| **Definition** | Validation | Проверка metadata tools/functions |
| **Request** | Sanitization | Очистка incoming parameters |
| **Execution** | Sandboxing | Изоляция выполнения tools |
| **Response** | Filtering | Удаление sensitive data |

---

## Лучшие практики

1. **Validate all definitions** — Не доверяйте tool descriptions
2. **Sanitize arguments** — Все параметры как untrusted
3. **Sandbox execution** — Изолируйте tool runtime
4. **Audit communications** — Логируйте все protocol messages
5. **Limit capabilities** — Минимально необходимые permissions

---

## Навигация

| Предыдущий | Текущий | Следующий |
|------------|---------|-----------|
| [Architectures](../01-architectures/) | **Protocols** | [Trust Boundaries](../03-trust/) |

---

*AI Security Academy | Подмодуль 04.2*
