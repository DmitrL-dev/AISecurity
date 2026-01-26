# Inference and Deployment

> **Level:** Beginner  
> **Time:** 45 minutes  
> **Track:** 01 — AI Fundamentals  
> **Module:** 01.2 — Training Lifecycle  
> **Version:** 1.0

---

## Learning Objectives

After completing this lesson, you will be able to:

- [ ] Explain the inference process for LLMs
- [ ] Understand optimizations: quantization, KV-cache, batching
- [ ] Describe deployment options: API, local, edge
- [ ] Understand security risks during inference

---

## 1. Inference: From Model to Response

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

### 1.2 Autoregressive Generation

```python
def generate(model, prompt_ids, max_tokens=100):
    """
    Autoregressive generation: one token at a time
    """
    generated = prompt_ids.clone()
    
    for _ in range(max_tokens):
        # Forward pass
        with torch.no_grad():
            logits = model(generated).logits
        
        # Get logits of last token
        next_logits = logits[:, -1, :]
        
        # Sampling
        probs = F.softmax(next_logits, dim=-1)
        next_token = torch.multinomial(probs, num_samples=1)
        
        # Add to context
        generated = torch.cat([generated, next_token], dim=-1)
        
        if next_token == eos_token_id:
            break
    
    return generated
```

### 1.3 Problem: Quadratic Complexity

```
Each new token requires attention to ALL previous tokens:

Token 1:    O(1) operations
Token 2:    O(2) operations  
Token 10:   O(10) operations
Token 100:  O(100) operations
Token 1000: O(1000) operations

Total for N tokens: O(N²)
```

---

## 2. Inference Optimizations

### 2.1 KV-Cache

**Idea:** Save Key and Value from previous tokens to avoid recomputation.

```python
class KVCacheAttention:
    def __init__(self):
        self.k_cache = None
        self.v_cache = None
    
    def forward(self, q, k, v, use_cache=True):
        if use_cache and self.k_cache is not None:
            # Add new K, V to cache
            k = torch.cat([self.k_cache, k], dim=1)
            v = torch.cat([self.v_cache, v], dim=1)
        
        # Save for next step
        self.k_cache = k
        self.v_cache = v
        
        # Attention
        return attention(q, k, v)
```

```
Without KV-Cache:
Step 1: Compute K,V for token 1
Step 2: Compute K,V for tokens 1,2
Step 3: Compute K,V for tokens 1,2,3  ← Redundant computation!

With KV-Cache:
Step 1: Compute K,V for token 1, cache
Step 2: Compute K,V for token 2 only, concat with cache
Step 3: Compute K,V for token 3 only, concat with cache
```

### 2.2 Quantization

**Idea:** Reduce weight precision for speedup and memory savings.

```
FP32: 32 bits per weight  →  70B model = 280 GB
FP16: 16 bits per weight  →  70B model = 140 GB
INT8:  8 bits per weight  →  70B model = 70 GB
INT4:  4 bits per weight  →  70B model = 35 GB
```

```python
# Example with bitsandbytes
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

### 2.3 Batching and Continuous Batching

```python
# Static Batching: all requests wait for the longest
batch = [
    "Hello",           # 1 token response
    "Write an essay"   # 500 token response
]
# "Hello" waits 500 steps!

# Continuous Batching: dynamic management
class ContinuousBatcher:
    def __init__(self):
        self.active_requests = []
    
    def step(self):
        # Generate token for all active requests
        for req in self.active_requests:
            next_token = generate_one_token(req)
            req.add_token(next_token)
            
            if next_token == EOS:
                self.complete_request(req)
                # Immediately add new request from queue!
                self.add_from_queue()
```

### 2.4 Speculative Decoding

**Idea:** Use small draft model for prediction, large model for verification.

```python
def speculative_decoding(large_model, small_model, prompt, k=4):
    """
    k draft tokens → verify all at once
    """
    # 1. Draft model generates k tokens
    draft_tokens = []
    for _ in range(k):
        token = small_model.generate_one(prompt + draft_tokens)
        draft_tokens.append(token)
    
    # 2. Large model verifies all k tokens with one forward pass
    # (instead of k separate passes!)
    verified = large_model.verify(prompt + draft_tokens)
    
    # 3. Accept matching tokens
    accepted = []
    for draft, verify in zip(draft_tokens, verified):
        if draft == verify:
            accepted.append(draft)
        else:
            accepted.append(verify)
            break  # Stop at first mismatch
    
    return accepted
```

---

## 3. Deployment Options

### 3.1 Options Comparison

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

### 3.3 Self-Hosted with vLLM

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
# Run as API server
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-2-7b-chat-hf \
    --port 8000
```

### 3.4 Edge Deployment

```python
# Ollama for local execution
import ollama

response = ollama.chat(
    model='llama3',
    messages=[{'role': 'user', 'content': 'Hello'}]
)

# llama.cpp via ctransformers
from ctransformers import AutoModelForCausalLM

model = AutoModelForCausalLM.from_pretrained(
    "TheBloke/Llama-2-7B-Chat-GGML",
    model_file="llama-2-7b-chat.q4_K_M.gguf",
    model_type="llama"
)
```

---

## 4. Inference Security

### 4.1 Inference-time Attacks

```
Inference Security Risks:
├── Prompt Injection (via user input)
├── Model Extraction (stealing via API)
├── Denial of Service (resource exhaustion)
├── Side-channel Attacks (timing, cache)
└── Output Manipulation (adversarial triggers)
```

### 4.2 Rate Limiting and Input Validation

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
# Detect model extraction attempts
class ExtractionDetector:
    def __init__(self):
        self.user_patterns = {}
    
    def check(self, user_id, prompt, response):
        # Extraction patterns:
        # - Many simple queries
        # - Queries for logits/embeddings
        # - Systematic probing patterns
        
        if user_id not in self.user_patterns:
            self.user_patterns[user_id] = []
        
        self.user_patterns[user_id].append({
            "prompt": prompt,
            "timestamp": time.time()
        })
        
        # Analyze patterns
        if self.is_extraction_pattern(user_id):
            return {"suspicious": True, "reason": "Potential extraction attempt"}
        
        return {"suspicious": False}
```

---

## 5. Practical Exercises

### Exercise 1: Quantization Comparison

```python
# Load model in different precisions and compare:
# - FP16
# - INT8
# - INT4

# Metrics:
# - Memory usage
# - Inference speed
# - Quality (perplexity)
```

### Exercise 2: vLLM Server

```bash
# Run vLLM server and test:
# - Throughput
# - Latency
# - Continuous batching effect
```

---

## 6. Quiz Questions

### Question 1

What is KV-Cache?

- [ ] A) Caching inference results
- [x] B) Saving Key and Value for reuse in attention
- [ ] C) Caching model weights
- [ ] D) Caching gradients

### Question 2

What effect does INT4 quantization have?

- [ ] A) Increases model quality
- [x] B) Reduces model size and speeds up inference
- [ ] C) Improves training
- [ ] D) Increases latency

### Question 3

What is Continuous Batching?

- [ ] A) Processing requests one by one
- [x] B) Dynamically adding/removing requests from batch during inference
- [ ] C) Grouping tokens
- [ ] D) Parallel training

---

## 7. Summary

In this lesson we learned:

1. **Inference pipeline:** Tokenization → Forward → Sampling → Decode
2. **KV-Cache:** Reusing Key/Value for speedup
3. **Quantization:** FP16 → INT8 → INT4 for memory savings
4. **Batching:** Static vs Continuous batching
5. **Deployment:** API, self-hosted, edge
6. **Security:** Validation, rate limiting, extraction prevention

---

## Next Lesson

→ [Module README](README.md)

---

*AI Security Academy | Track 01: AI Fundamentals | Module 01.2: Training Lifecycle*
