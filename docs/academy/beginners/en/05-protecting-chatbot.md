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

```python
from sentinel import scan

def protected_chat(user_message: str) -> str:
    # 1. Scan for threats
    result = scan(user_message)
    
    # 2. Block if dangerous
    if not result.is_safe:
        return "I cannot process this request."
    
    # 3. Safe to send to LLM
    response = llm.chat(user_message)
    return response
```

---

## Using the @guard Decorator

```python
from sentinel import guard

@guard(engines=["injection", "jailbreak", "pii"])
def my_chat(message: str) -> str:
    return openai.chat(message)

# Automatically protected!
result = my_chat("Hello!")
```

**On threat:** Raises `ThreatDetectedError`

---

## FastAPI Integration

```python
from fastapi import FastAPI
from sentinel.integrations.fastapi import SentinelMiddleware

app = FastAPI()

# Add protection to ALL endpoints
app.add_middleware(
    SentinelMiddleware,
    on_threat="block",  # Options: "block", "log", "warn"
    engines=["injection", "jailbreak"]
)

@app.post("/chat")
async def chat(message: str):
    return {"response": llm.chat(message)}
```

---

## Configuring Sensitivity

```python
from sentinel import configure

configure(
    threshold=0.7,  # Only block high confidence threats
    engines=["injection", "jailbreak"],
    on_threat="block"
)
```

| Threshold | Behavior |
|-----------|----------|
| 0.5 | Sensitive — may have false positives |
| 0.7 | Balanced (recommended) |
| 0.9 | Strict — only high confidence threats |

---

## Handling Blocked Requests

```python
from sentinel import scan
from sentinel.exceptions import ThreatDetectedError

try:
    result = scan(user_input)
    if not result.is_safe:
        # Log for investigation
        log_threat(result)
        # Return safe message
        return "I'm sorry, I can't help with that."
except ThreatDetectedError as e:
    return f"Security: {e.threat_type}"
```

---

## Best Practices

| Practice | Why |
|----------|-----|
| Scan ALL user input | Every input is a potential attack |
| Log threats | Understand attack patterns |
| Don't reveal details | "Injection blocked" helps attackers |
| Use @guard decorator | Cleaner code, harder to forget |

---

## Key Takeaways

1. **Scan before LLM** — never trust user input
2. **Use decorators** — @guard simplifies protection
3. **Configure thresholds** — balance security vs usability
4. **Log everything** — learn from attacks

---

## Next Lesson

→ [2.2: Testing Your Protection](./06-testing.md)
