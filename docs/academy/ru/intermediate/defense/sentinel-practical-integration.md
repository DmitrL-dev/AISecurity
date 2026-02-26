# Practical Интеграция

> **Level:** Intermediate  
> **Время:** 50 минут  
> **Track:** 03 — Defense Techniques  
> **Module:** 03.2 — SENTINEL Интеграция  
> **Version:** 1.0

---

## Цели обучения

- [ ] Integrate SENTINEL into real application
- [ ] Configure engines
- [ ] Create full protection pipeline

---

## 1. Basic Интеграция

### 1.1 Installation

```bash
pip install sentinel-brain
```

### 1.2 Quick Start

```rust
use sentinel_core::brain::SentinelBrain;

// Initialize
let brain = SentinelBrain::new(None);

// Protect a request
let result = brain.protect(
    "You are a helpful assistant.",
    "Hello, how are you?",
    &my_llm_function,
);

println!("{}", result.response);
println!("{:?}", result.security_report);
```

---

## 2. Configuration

### 2.1 Engine Configuration

```rust
use sentinel_core::brain::SentinelBrain;
use sentinel_core::brain::config::EngineConfig;
use std::collections::HashMap;
use serde_json::json;

let config = EngineConfig {
    // Input engines
    input_engines: HashMap::from([
        ("prompt_injection".into(), json!({
            "enabled": true,
            "threshold": 0.7,
            "patterns": "default"
        })),
        ("jailbreak".into(), json!({
            "enabled": true,
            "types": ["persona", "encoding", "logic"]
        })),
        ("sanitizer".into(), json!({
            "enabled": true,
            "unicode_normalize": true,
            "max_length": 10000
        })),
    ]),

    // Output engines
    output_engines: HashMap::from([
        ("safety".into(), json!({
            "enabled": true,
            "dimensions": ["toxicity", "harm", "bias"]
        })),
        ("pii".into(), json!({
            "enabled": true,
            "entities": ["email", "phone", "ssn"],
            "action": "redact"
        })),
    ]),

    // Global settings
    global_settings: HashMap::from([
        ("log_level".into(), json!("INFO")),
        ("fail_open".into(), json!(false)), // Block on error
        ("timeout_ms".into(), json!(5000)),
    ]),
};

let brain = SentinelBrain::new(Some(config));
```

### 2.2 YAML Configuration

```yaml
# sentinel_config.yaml
sentinel:
  input_engines:
    prompt_injection:
      enabled: true
      threshold: 0.7
    jailbreak:
      enabled: true
    sanitizer:
      enabled: true
      unicode_normalize: true
      
  output_engines:
    safety:
      enabled: true
      dimensions:
        - toxicity
        - harm
    pii:
      enabled: true
      action: redact
      
  global:
    log_level: INFO
    fail_open: false
```

```rust
use sentinel_core::brain::SentinelBrain;
use sentinel_core::brain::config::load_config;

let config = load_config("sentinel_config.yaml");
let brain = SentinelBrain::new(Some(config));
```

---

## 3. Интеграция Patterns

### 3.1 Wrapper Pattern

```rust
use sentinel_core::brain::SentinelBrain;

struct ProtectedLLM {
    llm: LLMClient,
    system_prompt: String,
    brain: SentinelBrain,
}

impl ProtectedLLM {
    fn new(llm_client: LLMClient, system_prompt: &str) -> Self {
        Self {
            llm: llm_client,
            system_prompt: system_prompt.to_string(),
            brain: SentinelBrain::new(None),
        }
    }

    fn chat(&self, user_input: &str) -> String {
        let result = self.brain.protect(
            &self.system_prompt,
            user_input,
            &|system, user| self.call_llm(system, user),
        );

        if result.blocked {
            return "I cannot process this request.".to_string();
        }

        result.response
    }

    fn call_llm(&self, system: &str, user: &str) -> String {
        let response = self.llm.chat.completions.create(
            "gpt-4",
            &[
                Message { role: "system", content: system },
                Message { role: "user", content: user },
            ],
        );
        response.choices[0].message.content.clone()
    }
}

// Usage
let protected = ProtectedLLM::new(openai_client, "You are a helpful assistant.");
let response = protected.chat("Hello!");
```

### 3.2 Middleware Pattern (FastAPI)

```rust
use actix_web::{web, App, HttpServer, HttpRequest, HttpResponse, middleware};
use sentinel_core::brain::SentinelBrain;
use serde::Deserialize;

struct AppState {
    brain: SentinelBrain,
}

#[derive(Deserialize)]
struct ChatRequest {
    message: String,
}

async fn sentinel_middleware(
    req: HttpRequest,
    body: web::Json<ChatRequest>,
    data: web::Data<AppState>,
) -> Result<HttpResponse, actix_web::Error> {
    // Only process chat endpoints
    if req.path().starts_with("/chat") {
        // Validate input
        let input_result = data.brain.validate_input(&body.message);

        if input_result.blocked {
            return Ok(HttpResponse::BadRequest()
                .json(serde_json::json!({"detail": input_result.reason})));
        }
    }

    Ok(HttpResponse::Ok().finish())
}

#[actix_web::post("/chat")]
async fn chat(
    data: web::Data<AppState>,
    body: web::Json<ChatRequest>,
) -> HttpResponse {
    let input_result = data.brain.validate_input(&body.message);

    // Generate response
    let response = generate_llm_response(&input_result.sanitized);

    // Validate output
    let output_result = data.brain.validate_output(&response);

    HttpResponse::Ok().json(serde_json::json!({"response": output_result.final_response}))
}
```

### 3.3 LangChain Интеграция

```rust
use sentinel_core::brain::SentinelBrain;

struct SentinelChain {
    llm: ChatOpenAI,
    brain: SentinelBrain,
    system_prompt: String,
}

impl SentinelChain {
    fn new(model_name: Option<&str>) -> Self {
        Self {
            llm: ChatOpenAI::new(model_name.unwrap_or("gpt-4")),
            brain: SentinelBrain::new(None),
            system_prompt: "You are a helpful assistant.".to_string(),
        }
    }

    fn invoke(&self, user_input: &str) -> String {
        // Pre-process with SENTINEL
        let input_result = self.brain.validate_input(user_input);

        if input_result.blocked {
            return format!("Request blocked: {}", input_result.reason);
        }

        // Generate response
        let messages = vec![
            Message::system(&self.system_prompt),
            Message::human(&input_result.sanitized),
        ];
        let response = self.llm.invoke(&messages);

        // Post-process with SENTINEL
        let output_result = self.brain.validate_output(&response.content);

        output_result.final_response
    }
}

// Usage
let chain = SentinelChain::new(None);
let result = chain.invoke("Hello, how are you?");
```

---

## 4. Monitoring and Logging

### 4.1 Security Logging

```rust
use sentinel_core::brain::SentinelBrain;
use sentinel_core::brain::logging::SecurityLogger;

// Configure logging
let logger = SecurityLogger::new(
    "file",                       // output
    "./logs/sentinel.log",        // path
    "json",                       // format
    true,                         // include_inputs: Log sanitized inputs
    false,                        // include_outputs: Don't log outputs (privacy)
);

let brain = SentinelBrain::with_logger(logger);

// All security events are automatically logged
let result = brain.protect(/* ... */);

// Manual logging
brain.logger().log_event(
    "custom_security_event",
    "warning",
    &serde_json::json!({"custom": "data"}),
);
```

### 4.2 Metrics

```rust
use sentinel_core::brain::metrics::MetricsCollector;

let metrics = MetricsCollector::new();

// After processing
metrics.record_request(
    result.input_analysis.blocked,
    result.output_analysis.blocked,
    result.processing_time,
);

// Get statistics
let stats = metrics.get_stats();
println!("Block rate: {}%", stats.block_rate);
println!("Avg processing time: {}ms", stats.avg_processing_time);
```

---

## 5. Error Handling

### 5.1 Graceful Degradation

```rust
use sentinel_core::brain::SentinelBrain;
use sentinel_core::brain::exceptions::SentinelError;

let brain = SentinelBrain::new(Some(config_with_fail_closed()));

match brain.protect(
    system,
    user_input,
    &generate,
) {
    Ok(result) => result.response,
    Err(SentinelError(e)) => {
        // Log the error
        tracing::error!("SENTINEL error: {}", e);

        // Fail closed - don't process request
        "Service temporarily unavailable. Please try again.".to_string()
    }
}
```

---

## 6. Practical Exercises

### Exercise 1: FastAPI Интеграция

```rust
// Create an actix-web app with SENTINEL protection
// Requirements:
// 1. POST /chat endpoint
// 2. Input validation with SENTINEL
// 3. Output filtering with PII redaction
// 4. Security logging
```

### Exercise 2: Custom Engine

```rust
// Create a custom engine for domain-specific filtering
// Пример: Block requests about competitors

use sentinel_core::scan; // Public API

struct CompetitorFilter {
    competitors: Vec<String>,
}

impl BaseEngine for CompetitorFilter {
    fn new(competitors: Vec<String>) -> Self {
        Self { competitors }
    }

    fn analyze(&self, text: &str) -> std::collections::HashMap<String, serde_json::Value> {
        // Your implementation
        todo!()
    }
}
```

---

## 7. Summary

1. **Installation:** `pip install sentinel-brain`
2. **Configuration:** Python dict or YAML
3. **Patterns:** Wrapper, Middleware, LangChain
4. **Monitoring:** Security logging, metrics
5. **Error handling:** Fail open vs fail closed

---

## Next Module

→ [Track 03 Summary](../README.md)

---

*AI Security Academy (RU) | Track 03: Defense Techniques | Module 03.2: SENTINEL Интеграция*
