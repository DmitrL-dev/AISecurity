# Practical Integration

> **Уровень:** Средний  
> **Время:** 50 минут  
> **Трек:** 03 — Defense Techniques  
> **Модуль:** 03.2 — SENTINEL Integration  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Интегрировать SENTINEL в реальное приложение
- [ ] Настроить конфигурацию engines
- [ ] Создать полный protection pipeline

---

## 1. Базовая интеграция

### 1.1 Installation

```bash
pip install sentinel-brain
```

### 1.2 Quick Start

```python
from sentinel.brain import SENTINELBrain

# Initialize
brain = SENTINELBrain()

# Protect a request
result = brain.protect(
    system_prompt="You are a helpful assistant.",
    user_input="Hello, how are you?",
    llm_fn=my_llm_function
)

print(result.response)
print(result.security_report)
```

---

## 2. Configuration

### 2.1 Engine Configuration

```python
from sentinel.brain import SENTINELBrain
from sentinel.brain.config import EngineConfig

config = EngineConfig(
    # Input engines
    input_engines={
        "prompt_injection": {
            "enabled": True,
            "threshold": 0.7,
            "patterns": "default"
        },
        "jailbreak": {
            "enabled": True,
            "types": ["persona", "encoding", "logic"]
        },
        "sanitizer": {
            "enabled": True,
            "unicode_normalize": True,
            "max_length": 10000
        }
    },
    
    # Output engines
    output_engines={
        "safety": {
            "enabled": True,
            "dimensions": ["toxicity", "harm", "bias"]
        },
        "pii": {
            "enabled": True,
            "entities": ["email", "phone", "ssn"],
            "action": "redact"
        }
    },
    
    # Global settings
    global_settings={
        "log_level": "INFO",
        "fail_open": False,  # Block on error
        "timeout_ms": 5000
    }
)

brain = SENTINELBrain(config)
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

```python
from sentinel.brain import SENTINELBrain
from sentinel.brain.config import load_config

config = load_config("sentinel_config.yaml")
brain = SENTINELBrain(config)
```

---

## 3. Integration Patterns

### 3.1 Wrapper Pattern

```python
from sentinel.brain import SENTINELBrain

class ProtectedLLM:
    def __init__(self, llm_client, system_prompt: str):
        self.llm = llm_client
        self.system_prompt = system_prompt
        self.brain = SENTINELBrain()
    
    def chat(self, user_input: str) -> str:
        result = self.brain.protect(
            system_prompt=self.system_prompt,
            user_input=user_input,
            llm_fn=self._call_llm
        )
        
        if result.blocked:
            return "I cannot process this request."
        
        return result.response
    
    def _call_llm(self, system: str, user: str) -> str:
        response = self.llm.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ]
        )
        return response.choices[0].message.content

# Usage
protected = ProtectedLLM(openai_client, "You are a helpful assistant.")
response = protected.chat("Hello!")
```

### 3.2 Middleware Pattern (FastAPI)

```python
from fastapi import FastAPI, Request, HTTPException
from sentinel.brain import SENTINELBrain

app = FastAPI()
brain = SENTINELBrain()

@app.middleware("http")
async def sentinel_middleware(request: Request, call_next):
    # Only process chat endpoints
    if request.url.path.startswith("/chat"):
        body = await request.json()
        
        # Validate input
        input_result = brain.validate_input(body.get("message", ""))
        
        if input_result.blocked:
            raise HTTPException(
                status_code=400, 
                detail=input_result.reason
            )
        
        # Store sanitized input
        request.state.sanitized_input = input_result.sanitized
    
    response = await call_next(request)
    return response

@app.post("/chat")
async def chat(request: Request):
    user_input = request.state.sanitized_input
    
    # Generate response
    response = generate_llm_response(user_input)
    
    # Validate output
    output_result = brain.validate_output(response)
    
    return {"response": output_result.final_response}
```

### 3.3 LangChain Integration

```python
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from sentinel.brain import SENTINELBrain

class SENTINELChain:
    def __init__(self, model_name: str = "gpt-4"):
        self.llm = ChatOpenAI(model=model_name)
        self.brain = SENTINELBrain()
        self.system_prompt = "You are a helpful assistant."
    
    def invoke(self, user_input: str) -> str:
        # Pre-process with SENTINEL
        input_result = self.brain.validate_input(user_input)
        
        if input_result.blocked:
            return f"Request blocked: {input_result.reason}"
        
        # Generate response
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=input_result.sanitized)
        ]
        response = self.llm.invoke(messages)
        
        # Post-process with SENTINEL
        output_result = self.brain.validate_output(response.content)
        
        return output_result.final_response

# Usage
chain = SENTINELChain()
result = chain.invoke("Hello, how are you?")
```

---

## 4. Monitoring и Logging

### 4.1 Security Logging

```python
from sentinel.brain import SENTINELBrain
from sentinel.brain.logging import SecurityLogger

# Configure logging
logger = SecurityLogger(
    output="file",
    path="./logs/sentinel.log",
    format="json",
    include_inputs=True,  # Log sanitized inputs
    include_outputs=False  # Don't log outputs (privacy)
)

brain = SENTINELBrain(logger=logger)

# All security events are automatically logged
result = brain.protect(...)

# Manual logging
logger.log_event(
    event_type="custom_security_event",
    severity="warning",
    details={"custom": "data"}
)
```

### 4.2 Metrics

```python
from sentinel.brain.metrics import MetricsCollector

metrics = MetricsCollector()

# After processing
metrics.record_request(
    input_blocked=result.input_analysis.blocked,
    output_blocked=result.output_analysis.blocked,
    processing_time_ms=result.processing_time
)

# Get statistics
stats = metrics.get_stats()
print(f"Block rate: {stats.block_rate}%")
print(f"Avg processing time: {stats.avg_processing_time}ms")
```

---

## 5. Error Handling

### 5.1 Graceful Degradation

```python
from sentinel.brain import SENTINELBrain
from sentinel.brain.exceptions import SENTINELError

brain = SENTINELBrain(config={"fail_open": False})

try:
    result = brain.protect(
        system_prompt=system,
        user_input=user_input,
        llm_fn=generate
    )
    return result.response
    
except SENTINELError as e:
    # Log the error
    logger.error(f"SENTINEL error: {e}")
    
    # Fail closed - don't process request
    return "Service temporarily unavailable. Please try again."
```

---

## 6. Практические задания

### Задание 1: FastAPI Integration

```python
# Create a FastAPI app with SENTINEL protection
# Requirements:
# 1. POST /chat endpoint
# 2. Input validation with SENTINEL
# 3. Output filtering with PII redaction
# 4. Security logging
```

### Задание 2: Custom Engine

```python
# Create a custom engine for domain-specific filtering
# Example: Block requests about competitors

from sentinel import scan  # Public API

class CompetitorFilter(BaseEngine):
    def __init__(self, competitors: list):
        self.competitors = competitors
    
    def analyze(self, text: str) -> dict:
        # Your implementation
        pass
```

---

## 7. Резюме

1. **Installation:** `pip install sentinel-brain`
2. **Configuration:** Python dict или YAML
3. **Patterns:** Wrapper, Middleware, LangChain
4. **Monitoring:** Security logging, metrics
5. **Error handling:** Fail open vs fail closed

---

## Следующий модуль

> [Track 03 Summary](../README.md)

---

*AI Security Academy | Track 03: Defense Techniques | Module 03.2: SENTINEL Integration*
