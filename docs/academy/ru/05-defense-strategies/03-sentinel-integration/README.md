# SENTINEL Integration

> **Подмодуль 05.3: Интеграция с платформой SENTINEL**

---

## Обзор

SENTINEL предоставляет комплексные инструменты безопасности ИИ. Этот подмодуль охватывает паттерны интеграции для типовых use cases.

---

## Quick Start

```python
from sentinel import scan, configure

# Конфигурация engines
configure(engines=["injection", "jailbreak", "pii"])

# Сканирование ввода
result = scan(user_input)
if not result.is_safe:
    raise SecurityError(result.threats)

# Безопасная обработка
response = await llm.generate(user_input)
```

---

## Паттерны интеграции

| Паттерн | Use Case | Сложность |
|---------|----------|-----------|
| **API Protection** | REST endpoints | Низкая |
| **Middleware** | Framework integration | Средняя |
| **Decorator** | Function protection | Низкая |
| **Pipeline** | Full processing | Средняя |

---

## Уроки

### 01. Basic Integration
**Время:** 35 минут | **Сложность:** Низкая

Базовое использование:
- scan() function
- Configuration
- Error handling
- Logging

### 02. ����������� Patterns
**Время:** 40 минут | **Сложность:** Средняя

Продвинутые паттерны:
- Custom engines
- Performance tuning
- High availability
- Monitoring

---

## Пример: API Protection

```python
from fastapi import FastAPI, HTTPException
from sentinel import scan

app = FastAPI()

@app.post("/chat")
async def chat(request: ChatRequest):
    # Check input
    if not scan(request.message).is_safe:
        raise HTTPException(400, "Blocked")
    
    # Generate response
    response = await llm.generate(request.message)
    
    # Check output
    if not scan(response, mode="output").is_safe:
        return {"response": "[Filtered]"}
    
    return {"response": response}
```

---

## Навигация

| Предыдущий | Текущий | Следующий |
|------------|---------|-----------|
| [Response](../02-response/) | **SENTINEL** | [Продвинутое](../../06-�����������/) |

---

*AI Security Academy | Подмодуль 05.3*
