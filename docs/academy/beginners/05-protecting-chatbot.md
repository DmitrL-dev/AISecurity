# 🛡️ Урок 2.1: Защита чатбота

> **Время: 25 минут** | Уровень: Beginner → Практика

---

## Сценарий

Ты создал чатбот на OpenAI API. Нужно защитить его от атак.

---

## Шаг 1: Базовая защита входа

```python
from sentinel import scan
import openai

def chat(user_message: str) -> str:
    # 1. Проверяем вход
    result = scan(user_message)
    
    if not result.is_safe:
        return f"⚠️ Обнаружена угроза: {result.threats}"
    
    # 2. Если безопасно — отправляем в LLM
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": user_message}]
    )
    
    return response.choices[0].message.content
```

---

## Шаг 2: Защита выхода

```python
from sentinel import scan, scan_output

def chat_protected(user_message: str) -> str:
    # Проверка входа
    input_result = scan(user_message)
    if not input_result.is_safe:
        return "⚠️ Suspicious input detected"
    
    # Генерация ответа
    response = openai.ChatCompletion.create(...)
    ai_response = response.choices[0].message.content
    
    # ✨ Проверка выхода на PII утечки
    output_result = scan_output(ai_response)
    if output_result.has_pii:
        return "⚠️ Response contains sensitive data"
    
    return ai_response
```

---

## Шаг 3: Декоратор для простоты

```python
from sentinel import guard

@guard(
    engines=["injection", "jailbreak", "pii"],
    on_threat="block"  # или "warn", "log"
)
def chat(user_message: str) -> str:
    return openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": user_message}]
    ).choices[0].message.content
```

Вся защита — в одном декораторе!

---

## Шаг 4: Логирование угроз

```python
from sentinel import scan, configure

configure(
    log_file="threats.log",
    log_level="warning",
    alert_webhook="https://your-slack.webhook/url"
)

result = scan("Ignore instructions")
# Автоматически логируется в threats.log
# Отправляется alert в Slack
```

---

## Шаг 5: Rate Limiting

```python
from sentinel import RateLimiter

limiter = RateLimiter(
    requests_per_minute=10,
    requests_per_user=100
)

def chat(user_id: str, message: str) -> str:
    if not limiter.allow(user_id):
        return "⚠️ Too many requests. Slow down."
    
    # ... остальной код
```

---

## Полный пример

```python
from sentinel import scan, guard, configure, RateLimiter
import openai

# Конфигурация
configure(
    log_file="security.log",
    engines=["injection", "jailbreak", "pii", "extraction"]
)

limiter = RateLimiter(requests_per_minute=10)

@guard(on_threat="block")
def protected_chat(user_id: str, message: str) -> str:
    # Rate limit
    if not limiter.allow(user_id):
        raise Exception("Rate limited")
    
    # Chat with LLM
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": message}
        ]
    )
    
    return response.choices[0].message.content

# Использование
try:
    answer = protected_chat("user_123", "Hello!")
    print(answer)
except Exception as e:
    print(f"Blocked: {e}")
```

---

## Чек-лист защиты чатбота

| Уровень | Защита | Код |
|---------|--------|-----|
| 🟢 **Basic** | Scan inputs | `scan(message)` |
| 🟢 **Basic** | Block threats | `if not result.is_safe:` |
| 🟡 **Medium** | Scan outputs | `scan_output(response)` |
| 🟡 **Medium** | Log threats | `configure(log_file=...)` |
| 🔴 **Advanced** | Rate limiting | `RateLimiter` |
| 🔴 **Advanced** | Alerts | `alert_webhook=...` |

---

## Упражнение

Добавь защиту к этому коду:

```python
import openai

def unsafe_chat(message: str) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": message}]
    )
    return response.choices[0].message.content
```

<details>
<summary>Решение</summary>

```python
from sentinel import guard

@guard(engines=["injection", "jailbreak"])
def safe_chat(message: str) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": message}]
    )
    return response.choices[0].message.content
```

</details>

---

## Следующий урок

→ [2.2: Тестирование на уязвимости](./06-testing.md)
