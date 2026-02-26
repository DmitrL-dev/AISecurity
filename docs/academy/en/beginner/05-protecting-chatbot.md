# 🛡️ Lesson 2.1: Protecting Your Chatbot

> **Time: 30 minutes** | Level: Beginner

---

## The Protection Flow

```
User Input → SENTINEL Scan → Safe? → LLM → Response
                    ↓
                 Blocked if threat
```

---

## Basic Protection

```rust
use sentinel_core::engines::SentinelEngine;

fn protected_chat(engine: &SentinelEngine, user_message: &str) -> String {
    // 1. Scan for threats
    let result = engine.analyze(user_message);

    // 2. Block if dangerous
    if result.detected {
        return "I cannot process this request.".to_string();
    }

    // 3. Safe to send to LLM
    let response = llm.chat(user_message);
    response
}
```

---

## Using a Guard Wrapper

```rust
use sentinel_core::engines::SentinelEngine;

fn guarded_chat(engine: &SentinelEngine, message: &str) -> Result<String, String> {
    let result = engine.analyze(message);
    if result.detected {
        return Err(format!("Threat detected: {:?}", result.categories));
    }
    Ok(llm.chat(message))
}

// Automatically protected!
let result = guarded_chat(&engine, "Hello!");
```

**On threat:** Returns `Err` with detected categories

---

## Actix-web Integration

```rust
use actix_web::{web, App, HttpServer, HttpResponse};
use sentinel_core::engines::SentinelEngine;

async fn chat(
    engine: web::Data<SentinelEngine>,
    message: web::Json<String>,
) -> HttpResponse {
    let result = engine.analyze(&message);
    if result.detected {
        return HttpResponse::Forbidden().body("Threat detected");
    }
    HttpResponse::Ok().json(llm.chat(&message))
}

HttpServer::new(move || {
    App::new()
        .app_data(web::Data::new(SentinelEngine::new()))
        .route("/chat", web::post().to(chat))
})
```

---

## Configuring Sensitivity

```rust
use sentinel_core::engines::SentinelEngine;

let engine = SentinelEngine::new();
let result = engine.analyze(user_input);

// Only block high confidence threats
if result.risk_score >= 0.7 {
    println!("Blocked: risk {}", result.risk_score);
}
```

| Threshold | Behavior |
|-----------|----------|
| 0.5 | Sensitive — may have false positives |
| 0.7 | Balanced (recommended) |
| 0.9 | Strict — only high confidence threats |

---

## Handling Blocked Requests

```rust
use sentinel_core::engines::SentinelEngine;

let engine = SentinelEngine::new();
let result = engine.analyze(user_input);

if result.detected {
    // Log for investigation
    eprintln!("Threat: {:?} (risk: {})", result.categories, result.risk_score);
    // Return safe message
    println!("I'm sorry, I can't help with that.");
} else {
    // Safe to process
    let response = llm.chat(user_input);
}
```

---

## Best Practices

| Practice | Why |
|----------|-----|
| Scan ALL user input | Every input is a potential attack |
| Log threats | Understand attack patterns |
| Don't reveal details | "Injection blocked" helps attackers |
| Use guard wrappers | Cleaner code, harder to forget |

---

## Key Takeaways

1. **Scan before LLM** — never trust user input
2. **Use guard wrappers** — encapsulate scan logic for reuse
3. **Configure thresholds** — balance security vs usability
4. **Log everything** — learn from attacks

---

## Next Lesson

→ [2.2: Testing Your Protection](./06-testing.md)
