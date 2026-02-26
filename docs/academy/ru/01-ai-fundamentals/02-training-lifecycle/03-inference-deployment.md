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

```python
def generate(model, prompt_ids, max_tokens=100):
    """
    Авторегрессивная генерация: по одному токену за раз
    """
    generated = prompt_ids.clone()
    
    for _ in range(max_tokens):
        # Forward pass
        with torch.no_grad():
            logits = model(generated).logits
        
        # Получаем logits последнего токена
        next_logits = logits[:, -1, :]
        
        # Sampling
        probs = F.softmax(next_logits, dim=-1)
        next_token = torch.multinomial(probs, num_samples=1)
        
        # Добавляем в контекст
        generated = torch.cat([generated, next_token], dim=-1)
        
        if next_token == eos_token_id:
            break
    
    return generated
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

```python
class KVCacheAttention:
    def __init__(self):
        self.k_cache = None
        self.v_cache = None
    
    def forward(self, q, k, v, use_cache=True):
        if use_cache and self.k_cache is not None:
            # Добавляем новые K, V в cache
            k = torch.cat([self.k_cache, k], dim=1)
            v = torch.cat([self.v_cache, v], dim=1)
        
        # Сохраняем для следующего шага
        self.k_cache = k
        self.v_cache = v
        
        # Attention
        return attention(q, k, v)
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

```python
# Пример с bitsandbytes
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

# 4-bit quantization
quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_quant_type="nf4",  # Normalized Float 4
)

model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-70b-hf",
    quantization_config=quantization_config,
    device_map="auto"
)
```

### 2.3 Batching и Continuous Batching

```python
# Static Batching: все запросы ждут самого длинного
batch = [
    "Hello",           # 1 токен ответа
    "Write an essay"   # 500 токенов ответа
]
# "Hello" ждёт 500 шагов!

# Continuous Batching: динамическое управление
class ContinuousBatcher:
    def __init__(self):
        self.active_requests = []
    
    def step(self):
        # Генерируем токен для всех активных запросов
        for req in self.active_requests:
            next_token = generate_one_token(req)
            req.add_token(next_token)
            
            if next_token == EOS:
                self.complete_request(req)
                # Сразу добавляем новый запрос из очереди!
                self.add_from_queue()
```

### 2.4 Speculative Decoding

**Идея:** Используем маленькую draft модель для предсказания, большую для верификации.

```python
def speculative_decoding(large_model, small_model, prompt, k=4):
    """
    k draft токенов → верифицируем все за раз
    """
    # 1. Draft модель генерирует k токенов
    draft_tokens = []
    for _ in range(k):
        token = small_model.generate_one(prompt + draft_tokens)
        draft_tokens.append(token)
    
    # 2. Большая модель верифицирует все k токенов одним forward pass
    # (вместо k отдельных passes!)
    verified = large_model.verify(prompt + draft_tokens)
    
    # 3. Принимаем matching токены
    accepted = []
    for draft, verify in zip(draft_tokens, verified):
        if draft == verify:
            accepted.append(draft)
        else:
            accepted.append(verify)
            break  # Останавливаемся на первом mismatch
    
    return accepted
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

```python
# OpenAI API
from openai import OpenAI
client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}]
)

# Anthropic API
from anthropic import Anthropic
client = Anthropic()

response = client.messages.create(
    model="claude-3-opus-20240229",
    messages=[{"role": "user", "content": "Hello"}]
)
```

### 3.3 Self-Hosted с vLLM

```python
# vLLM: high-performance inference server
from vllm import LLM, SamplingParams

llm = LLM(model="meta-llama/Llama-2-7b-chat-hf")

sampling_params = SamplingParams(
    temperature=0.8,
    top_p=0.95,
    max_tokens=512
)

outputs = llm.generate(["Hello, how are you?"], sampling_params)
```

```bash
# Запуск как API server
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-2-7b-chat-hf \
    --port 8000
```

### 3.4 Edge Deployment

```python
# Ollama для локального выполнения
import ollama

response = ollama.chat(
    model='llama3',
    messages=[{'role': 'user', 'content': 'Hello'}]
)

# llama.cpp через ctransformers
from ctransformers import AutoModelForCausalLM

model = AutoModelForCausalLM.from_pretrained(
    "TheBloke/Llama-2-7B-Chat-GGML",
    model_file="llama-2-7b-chat.q4_K_M.gguf",
    model_type="llama"
)
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

```python
from sentinel import scan  # Public API
    InputValidator,
    RateLimiter,
    OutputFilter
)

# Rate limiting
rate_limiter = RateLimiter(
    requests_per_minute=60,
    tokens_per_minute=100000
)

# Input validation
validator = InputValidator()

@app.post("/generate")
async def generate(request: GenerateRequest):
    # 1. Rate limit
    if not rate_limiter.check(request.user_id):
        raise HTTPException(429, "Rate limit exceeded")
    
    # 2. Input validation
    validation = validator.analyze(request.prompt)
    if validation.is_malicious:
        raise HTTPException(400, f"Invalid input: {validation.reason}")
    
    # 3. Generate
    response = model.generate(request.prompt)
    
    # 4. Output filtering
    filtered = output_filter.filter(response)
    
    return filtered
```

### 4.3 Предотвращение Model Extraction

```python
# Обнаружение попыток extraction
class ExtractionDetector:
    def __init__(self):
        self.user_patterns = {}
    
    def check(self, user_id, prompt, response):
        # Extraction паттерны:
        # - Много простых запросов
        # - Запросы на logits/embeddings
        # - Систематические probing паттерны
        
        if user_id not in self.user_patterns:
            self.user_patterns[user_id] = []
        
        self.user_patterns[user_id].append({
            "prompt": prompt,
            "timestamp": time.time()
        })
        
        # Анализируем паттерны
        if self.is_extraction_pattern(user_id):
            return {"suspicious": True, "reason": "Potential extraction attempt"}
        
        return {"suspicious": False}
```

---

## 5. Практические упражнения

### Упражнение 1: Сравнение Quantization

```python
# Загрузите модель в разных precision и сравните:
# - FP16
# - INT8
# - INT4

# Метрики:
# - Использование памяти
# - Скорость inference
# - Качество (perplexity)
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
