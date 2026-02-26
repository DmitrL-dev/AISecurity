# RLM Memory Integration

> Интеграция DevKit с RLM Memory Bridge для сохранения решений

## Назначение

RLM Memory Bridge используется для:
1. **Сохранения review decisions** — почему код был approved/rejected
2. **Накопления patterns** — часто встречающиеся issues
3. **Context restoration** — восстановление контекста в новых сессиях

---

## Архитектура

```
┌─────────────────┐     facts      ┌─────────────────┐
│  Reviewer Agent │ ────────────→  │  RLM Memory     │
│  Fixer Agent    │                │  Bridge         │
│  Security Audit │                │                 │
└─────────────────┘                └─────────────────┘
         ↓                                ↓
    Structured JSON                  L1/L2 Facts
```

---

## Паттерны хранения

### Review Decision (L1)

```python
# После Two-Stage Review
rlm_add_hierarchical_fact(
    content="Review APPROVED для engine XYZ: все payloads обнаружены, Clean Architecture соблюдена",
    level=1,  # L1 = session-level
    domain="devkit-review",
    module="engine-xyz"
)
```

### Rejected with Reason (L1)

```python
# При rejection
rlm_add_hierarchical_fact(
    content="Review REJECTED для engine XYZ: пропущен edge case с unicode input",
    level=1,
    domain="devkit-review",
    module="engine-xyz"
)
```

### Recurring Issue Pattern (L2)

```python
# При обнаружении повторяющегося паттерна
rlm_add_hierarchical_fact(
    content="Pattern: engines часто пропускают unicode edge cases. Добавить в checklist.",
    level=2,  # L2 = project-level
    domain="devkit-patterns"
)
```

### Security Finding (L2)

```python
# Критический security finding
rlm_add_hierarchical_fact(
    content="Security: обнаружен eval() в engine ABC — BLOCKING. CWE-94.",
    level=2,
    domain="devkit-security",
    ttl_days=365  # Долгосрочное хранение
)
```

---

## Интеграция с Prompts

### В reviewer.md добавить:

```
After completing review, store decision in RLM:

If APPROVED:
  rlm_add_hierarchical_fact(
    content="Review APPROVED: {module} - {summary}",
    level=1,
    domain="devkit-review"
  )

If REJECTED:
  rlm_add_hierarchical_fact(
    content="Review REJECTED: {module} - {issues}",
    level=1,
    domain="devkit-review"
  )
```

### В security-audit.md добавить:

```
For HIGH/CRITICAL findings:
  rlm_add_hierarchical_fact(
    content="Security Finding: {severity} in {file} - {description}",
    level=2,
    domain="devkit-security",
    ttl_days=365
  )
```

---

## Domains

| Domain | Уровень | Содержание |
|--------|---------|------------|
| `devkit-review` | L1 | Решения по review (approved/rejected) |
| `devkit-patterns` | L2 | Повторяющиеся паттерны issues |
| `devkit-security` | L2 | Security findings |
| `devkit-metrics` | L1 | Метрики (loop count, time to fix) |

---

## Восстановление контекста

При старте новой сессии:

```python
# Получить релевантный контекст
context = rlm_route_context(
    query="DevKit review patterns for engine development",
    max_tokens=2000
)

# Использовать в промптах
reviewer_prompt = f"""
Previous patterns to check:
{context}

Now review the following code...
"""
```

---

## MCP Integration

Для автоматического вызова из агента:

```python
# В конце review workflow
await mcp.call_tool(
    "rlm-toolkit",
    "rlm_add_hierarchical_fact",
    {
        "content": f"Review {status}: {module} - {summary}",
        "level": 1,
        "domain": "devkit-review"
    }
)
```

---

## Metrics Collection

Периодически сохранять метрики:

```python
rlm_add_hierarchical_fact(
    content=f"DevKit Metrics Week {week}: TDD compliance {pct}%, avg loop count {avg}, escape rate {rate}%",
    level=1,
    domain="devkit-metrics"
)
```

Использовать для трендов и улучшения процессов.
