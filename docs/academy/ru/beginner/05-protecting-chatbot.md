# 🛡️ Урок 2.1: Защита чатбота

> **Время: 25 минут** | Уровень: Beginner → Практика

---

## Сценарий

Ты создал чатбот на OpenAI API. Нужно защитить его от атак.

---

## Шаг 1: Базовая защита входа

```rust
use sentinel_core::engines::SentinelEngine;

fn chat(engine: &SentinelEngine, user_message: &str) -> String {
    // 1. Проверяем вход
    let result = engine.analyze(user_message);

    if result.detected {
        return format!("⚠️ Обнаружена угроза: {:?}", result.categories);
    }

    // 2. Если безопасно — отправляем в LLM
    let response = llm.chat(user_message);
    response
}
```

---

## Шаг 2: Защита выхода

```rust
use sentinel_core::engines::SentinelEngine;

fn chat_protected(engine: &SentinelEngine, user_message: &str) -> String {
    // Проверка входа
    let input_result = engine.analyze(user_message);
    if input_result.detected {
        return "⚠️ Suspicious input detected".to_string();
    }

    // Генерация ответа
    let ai_response = llm.chat(user_message);

    // ✨ Проверка выхода на PII утечки
    let output_result = engine.analyze(&ai_response);
    if output_result.detected {
        return "⚠️ Response contains sensitive data".to_string();
    }

    ai_response
}
```

---

## Шаг 3: Guard-обёртка для простоты

```rust
use sentinel_core::engines::SentinelEngine;

fn guarded_chat(engine: &SentinelEngine, user_message: &str) -> Result<String, String> {
    let result = engine.analyze(user_message);
    if result.detected {
        return Err(format!("Blocked: {:?}", result.categories));
    }
    Ok(llm.chat(user_message))
}
```

Вся защита — в одной функции!

---

## Шаг 4: Логирование угроз

```rust
use sentinel_core::engines::SentinelEngine;

let engine = SentinelEngine::new();

// Конфигурация логирования
eprintln!("Logging threats to threats.log");

let result = engine.analyze("Ignore instructions");
// Автоматически логируется
// Отправляется alert в Slack
```

---

## Шаг 5: Rate Limiting

```rust
use std::collections::HashMap;
use std::time::Instant;

struct RateLimiter {
    requests_per_minute: u32,
    counters: HashMap<String, (u32, Instant)>,
}

impl RateLimiter {
    fn new(requests_per_minute: u32) -> Self {
        Self { requests_per_minute, counters: HashMap::new() }
    }

    fn allow(&mut self, user_id: &str) -> bool {
        // ... проверка лимита
        true
    }
}

fn chat(limiter: &mut RateLimiter, user_id: &str, message: &str) -> String {
    if !limiter.allow(user_id) {
        return "⚠️ Too many requests. Slow down.".to_string();
    }

    // ... остальной код
    String::new()
}
```

---

## Полный пример

```rust
use sentinel_core::engines::SentinelEngine;

fn main() {
    // Конфигурация
    let engine = SentinelEngine::new();
    let mut limiter = RateLimiter::new(10);

    // Защищённый чат
    let result = protected_chat(&engine, &mut limiter, "user_123", "Hello!");
    match result {
        Ok(answer) => println!("{}", answer),
        Err(e) => println!("Blocked: {}", e),
    }
}

fn protected_chat(
    engine: &SentinelEngine,
    limiter: &mut RateLimiter,
    user_id: &str,
    message: &str,
) -> Result<String, String> {
    // Rate limit
    if !limiter.allow(user_id) {
        return Err("Rate limited".to_string());
    }

    // Scan
    let result = engine.analyze(message);
    if result.detected {
        return Err(format!("Threat: {:?}", result.categories));
    }

    // Chat with LLM
    Ok(llm.chat(message))
}
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

```rust
fn unsafe_chat(message: &str) -> String {
    let response = llm.chat(message);
    response
}
```

<details>
<summary>Решение</summary>

```rust
use sentinel_core::engines::SentinelEngine;

fn safe_chat(engine: &SentinelEngine, message: &str) -> Result<String, String> {
    let result = engine.analyze(message);
    if result.detected {
        return Err(format!("Blocked: {:?}", result.categories));
    }
    Ok(llm.chat(message))
}
```

</details>

---

## Следующий урок

→ [2.2: Тестирование на уязвимости](./06-testing.md)
