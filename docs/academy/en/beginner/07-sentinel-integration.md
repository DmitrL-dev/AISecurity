# 🔌 Lesson 2.3: SENTINEL Integration Patterns

> **Time: 30 minutes** | Level: Beginner

---

## Integration Options

| Pattern | Use Case | Complexity |
|---------|----------|------------|
| **Inline** | Simple scripts | Low |
| **Decorator** | Function protection | Low |
| **Middleware** | Web frameworks | Medium |
| **Sidecar** | Microservices | Medium |
| **Gateway** | Enterprise | High |

---

## Pattern 1: Inline

```rust
use sentinel_core::engines::SentinelEngine;

let engine = SentinelEngine::new();
let result = engine.analyze(user_input);
if !result.detected {
    let response = llm.chat(user_input);
}
```

**Pros:** Simple, explicit
**Cons:** Repetitive

---

## Pattern 2: Decorator

```rust
use sentinel_core::engines::SentinelEngine;

fn guarded_chat(engine: &SentinelEngine, message: &str) -> Result<String, String> {
    let result = engine.analyze(message);
    if result.detected {
        return Err(format!("Blocked: {:?}", result.categories));
    }
    Ok(llm.chat(message))
}
```

**Pros:** Clean, reusable
**Cons:** Less control

---

## Pattern 3: Middleware

```rust
// Actix-web middleware
use actix_web::{web, App, HttpServer};
use sentinel_core::engines::SentinelEngine;

HttpServer::new(move || {
    App::new()
        .app_data(web::Data::new(SentinelEngine::new()))
        .route("/chat", web::post().to(chat_handler))
})

// Axum middleware
use axum::{Router, Extension};
let app = Router::new()
    .route("/chat", post(chat_handler))
    .layer(Extension(SentinelEngine::new()));
```

---

## Pattern 4: Sidecar

```yaml
# docker-compose.yml
services:
  app:
    image: my-app
    environment:
      - SENTINEL_URL=http://sentinel:8080
  
  sentinel:
    image: sentinel/brain:latest
    ports:
      - "8080:8080"
```

```rust
// In your app
use reqwest;

async fn scan(text: &str) -> bool {
    let client = reqwest::Client::new();
    let resp: serde_json::Value = client
        .post("http://sentinel:8080/scan")
        .json(&serde_json::json!({"text": text}))
        .send().await.unwrap()
        .json().await.unwrap();
    !resp["detected"].as_bool().unwrap_or(false)
}
```

---

## Pattern 5: Gateway

```
Internet → SHIELD (DMZ) → Your App → LLM
              ↓
         All traffic scanned
```

Best for enterprise with multiple LLM services.

---

## Choosing a Pattern

| Your Situation | Recommended Pattern |
|----------------|---------------------|
| Simple script | Inline |
| Rust web app | Guard wrapper + Middleware |
| Microservices | Sidecar |
| Enterprise | Gateway (SHIELD) |

---

## Key Takeaways

1. **Multiple patterns available** — choose based on needs
2. **Start simple** — inline or decorator
3. **Scale up** — sidecar or gateway for production
4. **All patterns use same engines** — consistent protection

---

## Next Lesson

→ [3.1: Agentic AI Security](./08-agentic-security.md)
