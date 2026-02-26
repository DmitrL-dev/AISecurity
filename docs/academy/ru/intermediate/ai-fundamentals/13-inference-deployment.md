# Inference и Deployment

> **Уровень:** Beginner  
> **Время:** 45 минут  
> **Трек:** 01 — Основы AI  
> **Модуль:** 01.2 — Training Lifecycle  
> **Версия:** 1.0

---

## Цели обучения

После завершения этого урока вы сможете:

- [ ] Объяснить процесс inference для LLM
- [ ] Понять оптимизации: quantization, KV-cache, batching
- [ ] Описать варианты deployment: API, local, edge
- [ ] Понять риски безопасности во время inference

---

## 1. Inference: От модели к ответу

### 1.1 Inference Pipeline

```
┌────────────────────────────────────────────────────────────────────┐
│                     INFERENCE PIPELINE                              │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  User Prompt → Tokenizer → Model Forward Pass → Sampling → Decode │
│       ↓             ↓              ↓                ↓         ↓   │
│  "Hello"      [15496]      [logits]           [42]    "Hi"        │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 1.2 Авторегрессивная генерация

```rust
use candle_core::{Tensor, D};
use candle_nn::ops::softmax;

/// Авторегрессивная генерация: по одному токену за раз
fn generate(
    model: &dyn CausalLM,
    prompt_ids: &Tensor,
    max_tokens: usize,
    eos_token_id: u32,
) -> candle_core::Result<Tensor> {
    let mut generated = prompt_ids.clone();

    for _ in 0..max_tokens {
        // Forward pass
        let logits = model.forward(&generated)?;

        // Получаем logits последнего токена
        let seq_len = logits.dim(1)?;
        let next_logits = logits.narrow(1, seq_len - 1, 1)?.squeeze(1)?;

        // Sampling
        let probs = softmax(&next_logits, D::Minus1)?;
        let next_token = probs.multinomial(1)?;

        // Добавляем в контекст
        generated = Tensor::cat(&[&generated, &next_token], D::Minus1)?;

        if next_token.to_scalar::<u32>()? == eos_token_id {
            break;
        }
    }

    Ok(generated)
}
```

### 1.3 Проблема: Квадратичная сложность

```
Каждый новый токен требует attention ко ВСЕМ предыдущим токенам:

Token 1:    O(1) операций
Token 2:    O(2) операций  
Token 10:   O(10) операций
Token 100:  O(100) операций
Token 1000: O(1000) операций

Всего для N токенов: O(N²)
```

---

## 2. Оптимизации Inference

### 2.1 KV-Cache

**Идея:** Сохраняем Key и Value от предыдущих токенов чтобы избежать пересчёта.

```rust
use candle_core::{Tensor, D};

struct KVCacheAttention {
    k_cache: Option<Tensor>,
    v_cache: Option<Tensor>,
}

impl KVCacheAttention {
    fn new() -> Self {
        Self { k_cache: None, v_cache: None }
    }

    fn forward(
        &mut self,
        q: &Tensor,
        k: &Tensor,
        v: &Tensor,
        use_cache: bool,
    ) -> candle_core::Result<Tensor> {
        let (k, v) = if use_cache && self.k_cache.is_some() {
            // Добавляем новые K, V в cache
            let k = Tensor::cat(&[self.k_cache.as_ref().unwrap(), k], 1)?;
            let v = Tensor::cat(&[self.v_cache.as_ref().unwrap(), v], 1)?;
            (k, v)
        } else {
            (k.clone(), v.clone())
        };

        // Сохраняем для следующего шага
        self.k_cache = Some(k.clone());
        self.v_cache = Some(v.clone());

        // Attention
        attention(q, &k, &v)
    }
}
```

```
Без KV-Cache:
Шаг 1: Вычисляем K,V для токена 1
Шаг 2: Вычисляем K,V для токенов 1,2
Шаг 3: Вычисляем K,V для токенов 1,2,3  ← Избыточное вычисление!

С KV-Cache:
Шаг 1: Вычисляем K,V для токена 1, кэшируем
Шаг 2: Вычисляем K,V только для токена 2, конкатенируем с cache
Шаг 3: Вычисляем K,V только для токена 3, конкатенируем с cache
```

### 2.2 Quantization

**Идея:** Уменьшаем точность весов для ускорения и экономии памяти.

```
FP32: 32 бита на вес  →  70B модель = 280 GB
FP16: 16 бит на вес   →  70B модель = 140 GB
INT8:  8 бит на вес   →  70B модель = 70 GB
INT4:  4 бита на вес  →  70B модель = 35 GB
```

```rust
use candle_core::Device;

fn main() -> candle_core::Result<()> {
    let device = Device::Cpu;

    // 4-bit quantization with candle
    // candle поддерживает GGUF quantized models напрямую
    // let model = candle_transformers::quantized::gguf::load(
    //     "meta-llama/Llama-2-70b-hf.Q4_K_M.gguf",
    //     &device,
    // )?;

    // Quantization types: Q4_0, Q4_K_M, Q5_K_M, Q8_0
    // NF4 (Normalized Float 4) также поддерживается

    Ok(())
}
```

### 2.3 Batching и Continuous Batching

```rust
// Static Batching: все запросы ждут самого длинного
let batch = vec![
    "Hello",           // 1 токен ответа
    "Write an essay",  // 500 токенов ответа
];
// "Hello" ждёт 500 шагов!

// Continuous Batching: динамическое управление
struct ContinuousBatcher {
    active_requests: Vec<Request>,
}

impl ContinuousBatcher {
    fn step(&mut self) {
        // Генерируем токен для всех активных запросов
        let mut completed = Vec::new();
        for (i, req) in self.active_requests.iter_mut().enumerate() {
            let next_token = generate_one_token(req);
            req.add_token(next_token);

            if next_token == EOS {
                completed.push(i);
            }
        }
        // Удаляем завершённые и сразу добавляем новые из очереди
        for i in completed.into_iter().rev() {
            self.complete_request(i);
            self.add_from_queue();
        }
    }
}
```

### 2.4 Speculative Decoding

**Идея:** Используем маленькую draft модель для предсказания, большую для верификации.

```rust
/// k draft токенов → верифицируем все за раз
fn speculative_decoding(
    large_model: &dyn CausalLM,
    small_model: &dyn CausalLM,
    prompt: &[u32],
    k: usize,
) -> Vec<u32> {
    // 1. Draft модель генерирует k токенов
    let mut draft_tokens = Vec::new();
    for _ in 0..k {
        let mut context: Vec<u32> = prompt.to_vec();
        context.extend(&draft_tokens);
        let token = small_model.generate_one(&context);
        draft_tokens.push(token);
    }

    // 2. Большая модель верифицирует все k токенов одним forward pass
    // (вместо k отдельных passes!)
    let mut context: Vec<u32> = prompt.to_vec();
    context.extend(&draft_tokens);
    let verified = large_model.verify(&context);

    // 3. Принимаем matching токены
    let mut accepted = Vec::new();
    for (draft, verify) in draft_tokens.iter().zip(verified.iter()) {
        if draft == verify {
            accepted.push(*draft);
        } else {
            accepted.push(*verify);
            break; // Останавливаемся на первом mismatch
        }
    }

    accepted
}
```

---

## 3. Варианты Deployment

### 3.1 Сравнение вариантов

| Вариант | Latency | Privacy | Cost | Control |
|---------|---------|---------|------|---------|
| **API (OpenAI, Anthropic)** | Низкая | Низкая | Pay-per-use | Низкий |
| **Self-hosted Cloud** | Средняя | Высокая | Фиксированная | Высокий |
| **On-premise** | Средняя | Наивысшая | Capital | Наивысший |
| **Edge/Device** | Varies | Наивысшая | Низкая | Высокий |

### 3.2 API Deployment

```rust
// OpenAI API (via reqwest)
// use reqwest;
// let client = reqwest::Client::new();
// let response = client.post("https://api.openai.com/v1/chat/completions")
//     .json(&json!({"model": "gpt-4", "messages": [{"role": "user", "content": "Hello"}]}))
//     .send().await?;

// Anthropic API (via reqwest)
// let response = client.post("https://api.anthropic.com/v1/messages")
//     .json(&json!({"model": "claude-3-opus-20240229", "messages": [{"role": "user", "content": "Hello"}]}))
//     .send().await?;
```

### 3.3 Self-Hosted с vLLM

```rust
// vLLM: high-performance inference server (Rust equivalent)
// Using candle for self-hosted inference

use candle_core::Device;

fn main() -> candle_core::Result<()> {
    let device = Device::Cpu;

    // Load model via candle
    // let model = candle_transformers::models::llama::Llama::load(
    //     "meta-llama/Llama-2-7b-chat-hf", &device,
    // )?;

    struct SamplingParams {
        temperature: f64,
        top_p: f64,
        max_tokens: usize,
    }

    let sampling_params = SamplingParams {
        temperature: 0.8,
        top_p: 0.95,
        max_tokens: 512,
    };

    // let outputs = model.generate("Hello, how are you?", &sampling_params)?;

    Ok(())
}
```

```bash
# Запуск как API server
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-2-7b-chat-hf \
    --port 8000
```

### 3.4 Edge Deployment

```rust
// Ollama для локального выполнения (через HTTP API)
// let response = reqwest::Client::new()
//     .post("http://localhost:11434/api/chat")
//     .json(&json!({"model": "llama3", "messages": [{"role": "user", "content": "Hello"}]}))
//     .send().await?;

// llama.cpp через candle GGUF loader
// let model = candle_transformers::quantized::gguf::load(
//     "TheBloke/Llama-2-7B-Chat-GGML/llama-2-7b-chat.q4_K_M.gguf",
//     &Device::Cpu,
// )?;
```

---

## 4. Безопасность Inference

### 4.1 Inference-time атаки

```
Риски безопасности Inference:
├── Prompt Injection (через user input)
├── Model Extraction (кража через API)
├── Denial of Service (исчерпание ресурсов)
├── Side-channel Attacks (timing, cache)
└── Output Manipulation (adversarial triggers)
```

### 4.2 Rate Limiting и Input Validation

```rust
use sentinel_core::engines::{InputValidator, RateLimiter, OutputFilter};
use actix_web::{web, HttpResponse, post};

// Rate limiting
let rate_limiter = RateLimiter::new(
    60,      // requests_per_minute
    100000,  // tokens_per_minute
);

// Input validation
let validator = InputValidator::new();

#[post("/generate")]
async fn generate(request: web::Json<GenerateRequest>) -> HttpResponse {
    // 1. Rate limit
    if !rate_limiter.check(&request.user_id) {
        return HttpResponse::TooManyRequests().body("Rate limit exceeded");
    }

    // 2. Input validation
    let validation = validator.analyze(&request.prompt);
    if validation.is_malicious {
        return HttpResponse::BadRequest().body(format!("Invalid input: {}", validation.reason));
    }

    // 3. Generate
    let response = model.generate(&request.prompt).unwrap();

    // 4. Output filtering
    let filtered = output_filter.filter(&response);

    HttpResponse::Ok().json(filtered)
}
```

### 4.3 Предотвращение Model Extraction

```rust
use std::collections::HashMap;
use std::time::Instant;

/// Обнаружение попыток extraction
struct ExtractionDetector {
    user_patterns: HashMap<String, Vec<PatternEntry>>,
}

struct PatternEntry {
    prompt: String,
    timestamp: Instant,
}

impl ExtractionDetector {
    fn new() -> Self {
        Self { user_patterns: HashMap::new() }
    }

    fn check(&mut self, user_id: &str, prompt: &str, _response: &str) -> HashMap<String, serde_json::Value> {
        // Extraction паттерны:
        // - Много простых запросов
        // - Запросы на logits/embeddings
        // - Систематические probing паттерны

        self.user_patterns
            .entry(user_id.to_string())
            .or_default()
            .push(PatternEntry {
                prompt: prompt.to_string(),
                timestamp: Instant::now(),
            });

        // Анализируем паттерны
        if self.is_extraction_pattern(user_id) {
            let mut result = HashMap::new();
            result.insert("suspicious".into(), serde_json::json!(true));
            result.insert("reason".into(), serde_json::json!("Potential extraction attempt"));
            return result;
        }

        let mut result = HashMap::new();
        result.insert("suspicious".into(), serde_json::json!(false));
        result
    }
}
```

---

## 5. Практические упражнения

### Упражнение 1: Сравнение Quantization

```rust
// Загрузите модель в разных precision и сравните:
// - FP16
// - INT8
// - INT4

// Метрики:
// - Использование памяти
// - Скорость inference
// - Качество (perplexity)
```

### Упражнение 2: vLLM Server

```bash
# Запустите vLLM server и протестируйте:
# - Throughput
# - Latency
# - Эффект continuous batching
```

---

## 6. Quiz вопросы

### Вопрос 1

Что такое KV-Cache?

- [ ] A) Кэширование результатов inference
- [x] B) Сохранение Key и Value для переиспользования в attention
- [ ] C) Кэширование весов модели
- [ ] D) Кэширование градиентов

### Вопрос 2

Какой эффект имеет INT4 quantization?

- [ ] A) Увеличивает качество модели
- [x] B) Уменьшает размер модели и ускоряет inference
- [ ] C) Улучшает training
- [ ] D) Увеличивает latency

### Вопрос 3

Что такое Continuous Batching?

- [ ] A) Обработка запросов по одному
- [x] B) Динамическое добавление/удаление запросов из batch во время inference
- [ ] C) Группировка токенов
- [ ] D) Параллельное обучение

---

## 7. Резюме

В этом уроке мы изучили:

1. **Inference pipeline:** Tokenization → Forward → Sampling → Decode
2. **KV-Cache:** Переиспользование Key/Value для ускорения
3. **Quantization:** FP16 → INT8 → INT4 для экономии памяти
4. **Batching:** Static vs Continuous batching
5. **Deployment:** API, self-hosted, edge
6. **Security:** Валидация, rate limiting, предотвращение extraction

---

## Следующий урок

→ [Module README](README.md)

---

*AI Security Academy | Трек 01: Основы AI | Модуль 01.2: Training Lifecycle*
