# Inference и Deployment

> **Уровень:** Начинающий  
> **Время:** 45 минут  
> **Трек:** 01 — AI Fundamentals  
> **Модуль:** 01.2 — Жизненный цикл обучения  
> **Версия:** 1.0

---

## Цели обучения

После завершения этого урока вы сможете:

- [ ] Объяснить процесс inference для LLM
- [ ] Понять оптимизации: quantization, KV-cache, batching
- [ ] Описать deployment опции: API, local, edge
- [ ] Понять security риски на этапе inference

---

## 1. Inference: От модели к ответу

### 1.1 Inference Pipeline

```
---------------------------------------------------------------------¬
¦                     INFERENCE PIPELINE                              ¦
+--------------------------------------------------------------------+
¦                                                                    ¦
¦  User Prompt > Tokenizer > Model Forward Pass > Sampling > Decode ¦
¦       v             v              v                v         v   ¦
¦  "Hello"      [15496]      [logits]           [42]    "Hi"        ¦
¦                                                                    ¦
L---------------------------------------------------------------------
```

### 1.2 Autoregressive Generation

```python
def generate(model, prompt_ids, max_tokens=100):
    """
    Autoregressive generation: один токен за раз
    """
    generated = prompt_ids.clone()
    
    for _ in range(max_tokens):
        # Forward pass
        with torch.no_grad():
            logits = model(generated).logits
        
        # Берём logits последнего токена
        next_logits = logits[:, -1, :]
        
        # Sampling
        probs = F.softmax(next_logits, dim=-1)
        next_token = torch.multinomial(probs, num_samples=1)
        
        # Добавляем к контексту
        generated = torch.cat([generated, next_token], dim=-1)
        
        if next_token == eos_token_id:
            break
    
    return generated
```

### 1.3 Проблема: Квадратичная сложность

```
Каждый новый токен требует attention ко ВСЕМ предыдущим:

Token 1:    O(1) operations
Token 2:    O(2) operations  
Token 10:   O(10) operations
Token 100:  O(100) operations
Token 1000: O(1000) operations

Total для N токенов: O(N?)
```

---

## 2. Оптимизации Inference

### 2.1 KV-Cache

**Идея:** Сохранять Key и Value из предыдущих токенов, чтобы не пересчитывать.

```python
class KVCacheAttention:
    def __init__(self):
        self.k_cache = None
        self.v_cache = None
    
    def forward(self, q, k, v, use_cache=True):
        if use_cache and self.k_cache is not None:
            # Добавляем новые K, V к кэшу
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
Step 1: Compute K,V for token 1
Step 2: Compute K,V for tokens 1,2
Step 3: Compute K,V for tokens 1,2,3  < Повторные вычисления!

С KV-Cache:
Step 1: Compute K,V for token 1, cache
Step 2: Compute K,V for token 2 only, concat with cache
Step 3: Compute K,V for token 3 only, concat with cache
```

### 2.2 Quantization

**Идея:** Уменьшить precision весов для ускорения и экономии памяти.

```
FP32: 32 bits per weight  >  70B model = 280 GB
FP16: 16 bits per weight  >  70B model = 140 GB
INT8:  8 bits per weight  >  70B model = 70 GB
INT4:  4 bits per weight  >  70B model = 35 GB
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
# Static Batching: все запросы ждут самый длинный
batch = [
    "Hello",           # 1 token response
    "Write an essay"   # 500 token response
]
# "Hello" ждёт 500 шагов!

# Continuous Batching: динамическое управление
class ContinuousBatcher:
    def __init__(self):
        self.active_requests = []
    
    def step(self):
        # Генерируем токен для всех активных
        for req in self.active_requests:
            next_token = generate_one_token(req)
            req.add_token(next_token)
            
            if next_token == EOS:
                self.complete_request(req)
                # Сразу добавляем новый запрос из очереди!
                self.add_from_queue()
```

### 2.4 Speculative Decoding

**Идея:** Использовать маленькую draft модель для предсказания, большую для верификации.

```python
def speculative_decoding(large_model, small_model, prompt, k=4):
    """
    k draft токенов > verify all at once
    """
    # 1. Draft model генерирует k токенов
    draft_tokens = []
    for _ in range(k):
        token = small_model.generate_one(prompt + draft_tokens)
        draft_tokens.append(token)
    
    # 2. Large model проверяет все k токенов одним forward pass
    # (вместо k отдельных passes!)
    verified = large_model.verify(prompt + draft_tokens)
    
    # 3. Принимаем совпадающие токены
    accepted = []
    for draft, verify in zip(draft_tokens, verified):
        if draft == verify:
            accepted.append(draft)
        else:
            accepted.append(verify)
            break  # Останавливаемся на первом несовпадении
    
    return accepted
```

---

## 3. Deployment Options

### 3.1 Сравнение опций

| Option | Latency | Privacy | Cost | Control |
|--------|---------|---------|------|---------|
| **API (OpenAI, Anthropic)** | Low | Low | Pay-per-use | Low |
| **Self-hosted Cloud** | Medium | High | Fixed | High |
| **On-premise** | Medium | Highest | Capital | Highest |
| **Edge/Device** | Varies | Highest | Low | High |

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
# vLLM: высокопроизводительный inference server
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
# Ollama для локального запуска
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

## 4. Security в Inference

### 4.1 Inference-time Attacks

```
Inference Security Risks:
+-- Prompt Injection (через user input)
+-- Model Extraction (stealing через API)
+-- Denial of Service (resource exhaustion)
+-- Side-channel Attacks (timing, cache)
L-- Output Manipulation (adversarial triggers)
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

### 4.3 Model Extraction Prevention

```python
# Детекция model extraction attempts
class ExtractionDetector:
    def __init__(self):
        self.user_patterns = {}
    
    def check(self, user_id, prompt, response):
        # Паттерны extraction:
        # - Множество простых запросов
        # - Запросы для получения logits/embeddings
        # - Систематичные probing patterns
        
        if user_id not in self.user_patterns:
            self.user_patterns[user_id] = []
        
        self.user_patterns[user_id].append({
            "prompt": prompt,
            "timestamp": time.time()
        })
        
        # Анализ паттернов
        if self.is_extraction_pattern(user_id):
            return {"suspicious": True, "reason": "Potential extraction attempt"}
        
        return {"suspicious": False}
```

---

## 5. Практические задания

### Задание 1: Сравнение Quantization

```python
# Загрузите модель в разных precisions и сравните:
# - FP16
# - INT8
# - INT4

# Метрики:
# - Memory usage
# - Inference speed
# - Quality (perplexity)
```

### Задание 2: vLLM Server

```bash
# Запустите vLLM server и протестируйте:
# - Throughput
# - Latency
# - Continuous batching эффект
```

---

## 6. Проверочные вопросы

### Вопрос 1

Что такое KV-Cache?

- [ ] A) Кэширование результатов inference
- [x] B) Сохранение Key и Value для переиспользования в attention
- [ ] C) Кэширование весов модели
- [ ] D) Кэширование gradients

### Вопрос 2

Какой эффект даёт INT4 quantization?

- [ ] A) Увеличивает качество модели
- [x] B) Уменьшает размер модели и ускоряет inference
- [ ] C) Улучшает training
- [ ] D) Увеличивает latency

### Вопрос 3

Что такое Continuous Batching?

- [ ] A) Обработка запросов один за другим
- [x] B) Динамическое добавление/удаление запросов из batch во время inference
- [ ] C) Группировка токенов
- [ ] D) Параллельное обучение

---

## 7. Резюме

В этом уроке мы изучили:

1. **Inference pipeline:** Tokenization > Forward > Sampling > Decode
2. **KV-Cache:** Переиспользование Key/Value для ускорения
3. **Quantization:** FP16 > INT8 > INT4 для экономии памяти
4. **Batching:** Static vs Continuous batching
5. **Deployment:** API, self-hosted, edge
6. **Security:** Validation, rate limiting, extraction prevention

---

## Следующий урок

> [Module README](README.md)

---

*AI Security Academy | Track 01: AI Fundamentals | Module 01.2: Training Lifecycle*
