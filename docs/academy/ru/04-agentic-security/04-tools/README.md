# Безопасность инструментов

> **Подмодуль 04.4: Защита tool calling**

---

## Обзор

Tool calling — одна из ключевых capabilities агентов. Этот подмодуль охватывает безопасность вызовов инструментов, валидацию и аудит.

---

## Угрозы

| Угроза | Описание | Защита |
|--------|----------|--------|
| **Injection** | Вредоносные параметры | Validation |
| **Description** | Manipulation описания | Schema check |
| **Return value** | Вредоносный response | Output scan |
| **Overuse** | Excessive calls | Rate limiting |

---

## Уроки

### 01. Tool Validation
**Время:** 35 минут | **Сложность:** Средняя

Валидация инструментов:
- Schema validation
- Parameter sanitization
- Type checking
- Range limits

### 02. Description Security
**Время:** 35 минут | **Сложность:** Средняя

Защита описаний:
- Description injection attacks
- Malicious tool registration
- Static analysis
- Runtime verification

### 03. Output Verification
**Время:** 40 минут | **Сложность:** Средняя-Высокая

Проверка результатов:
- Output scanning
- PII detection
- Anomaly detection
- Chain validation

---

## Пример защиты

```python
from sentinel import scan

def safe_tool_call(tool_name, params):
    # 1. Валидация параметров
    if not validate_schema(params):
        raise SecurityError("Invalid params")
    
    # 2. Вызов инструмента
    result = call_tool(tool_name, params)
    
    # 3. Сканирование результата
    if not scan(result).is_safe:
        raise SecurityError("Unsafe output")
    
    return result
```

---

## Навигация

| Предыдущий | Текущий | Следующий |
|------------|---------|-----------|
| [Tool Security](../02-tool-security/) | **Tools** | [Defense Strategies](../../05-defense-strategies/) |

---

*AI Security Academy | Подмодуль 04.4*
