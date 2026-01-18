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

```python
from sentinel import scan

result = scan(user_input)
if result.is_safe:
    response = llm.chat(user_input)
```

**Pros:** Simple, explicit
**Cons:** Repetitive

---

## Pattern 2: Decorator

```python
from sentinel import guard

@guard(engines=["injection", "jailbreak"])
def chat(message: str) -> str:
    return llm.chat(message)
```

**Pros:** Clean, reusable
**Cons:** Less control

---

## Pattern 3: Middleware

```python
# FastAPI
from sentinel.integrations.fastapi import SentinelMiddleware
app.add_middleware(SentinelMiddleware, on_threat="block")

# Flask
from sentinel.integrations.flask import SentinelMiddleware
app.wsgi_app = SentinelMiddleware(app.wsgi_app)

# LangChain
from sentinel.integrations.langchain import SentinelCallback
chain.run(callbacks=[SentinelCallback()])
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

```python
# In your app
import requests

def scan(text):
    resp = requests.post("http://sentinel:8080/scan", json={"text": text})
    return resp.json()["is_safe"]
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
| Python web app | Decorator + Middleware |
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
