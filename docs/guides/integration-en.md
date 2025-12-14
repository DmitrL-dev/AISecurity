# 🔗 SENTINEL — Integration Guide

> **Reading time:** 25 minutes  
> **Level:** Intermediate  
> **Result:** SENTINEL integrated with your application and LLM provider

---

## Contents

1. [Integration Overview](#integration-overview)
2. [REST API Integration](#rest-api-integration)
3. [Python SDK](#python-sdk)
4. [JavaScript/TypeScript SDK](#javascripttypescript-sdk)
5. [OpenAI Integration](#openai-integration)
6. [LangChain Integration](#langchain-integration)
7. [Ollama Integration](#ollama-integration)
8. [Webhook Integration](#webhook-integration)
9. [Usage Examples](#usage-examples)

---

## Integration Overview

### Integration Methods

| Method           | Difficulty     | Use Case                   |
| ---------------- | -------------- | -------------------------- |
| **REST API**     | ⭐ Easy        | Any programming language   |
| **Python SDK**   | ⭐ Easy        | Python applications        |
| **JS/TS SDK**    | ⭐ Easy        | Node.js, browser           |
| **OpenAI Proxy** | ⭐⭐ Medium    | Drop-in OpenAI replacement |
| **LangChain**    | ⭐⭐ Medium    | LangChain applications     |
| **Webhook**      | ⭐⭐⭐ Complex | Event-driven architecture  |

---

## REST API Integration

### Basic Request

```bash
curl -X POST https://sentinel.your-domain.com/v1/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "text": "User input to analyze",
    "context": {
      "system_prompt": "You are a helpful assistant"
    }
  }'
```

### Response

```json
{
  "request_id": "req-abc123",
  "risk_score": 0.15,
  "verdict": "SAFE",
  "details": {
    "engines_triggered": [],
    "analysis_time_ms": 45
  },
  "recommendation": "ALLOW"
}
```

### Error Handling

```json
// 403 Forbidden (Blocked)
{
  "error": {
    "code": "content_blocked",
    "message": "Request blocked due to security concerns",
    "risk_score": 0.92,
    "engines_triggered": ["injection", "attack_2025"]
  }
}

// 429 Rate Limited
{
  "error": {
    "code": "rate_limit_exceeded",
    "retry_after": 45
  }
}
```

---

## Python SDK

### Installation

```bash
pip install sentinel-ai-security
```

### Basic Usage

```python
from sentinel import SentinelClient

client = SentinelClient(
    base_url="https://sentinel.your-domain.com",
    api_key="YOUR_API_KEY"
)

result = client.analyze("User input text")

if result.is_safe:
    print("✅ Safe to proceed")
else:
    print(f"⛔ Blocked: {result.reason}")
    print(f"Risk score: {result.risk_score}")
```

### Complete Example

```python
from sentinel import SentinelClient, AnalysisMode
from sentinel.exceptions import SentinelBlockedError, SentinelError

client = SentinelClient(
    base_url="https://sentinel.your-domain.com",
    api_key="YOUR_API_KEY",
    timeout=30,
    analysis_mode=AnalysisMode.BALANCED
)

def process_user_input(user_message: str) -> str:
    try:
        result = client.analyze(
            text=user_message,
            context={"user_id": "user123"}
        )

        if result.is_safe:
            llm_response = call_your_llm(user_message)
            output_result = client.analyze_output(llm_response)
            return llm_response if output_result.is_safe else "Filtered."
        else:
            return "Your request cannot be processed."

    except SentinelBlockedError as e:
        return "Request blocked for security reasons."
    except SentinelError as e:
        return "Service temporarily unavailable."
```

### Async Client

```python
import asyncio
from sentinel import AsyncSentinelClient

async def main():
    client = AsyncSentinelClient(
        base_url="https://sentinel.your-domain.com",
        api_key="YOUR_API_KEY"
    )

    messages = ["Hello!", "How are you?"]
    tasks = [client.analyze(msg) for msg in messages]
    results = await asyncio.gather(*tasks)

    for msg, result in zip(messages, results):
        print(f"{msg}: {result.verdict}")

asyncio.run(main())
```

---

## JavaScript/TypeScript SDK

### Installation

```bash
npm install @sentinel-ai/client
```

### Basic Usage

```typescript
import { SentinelClient } from "@sentinel-ai/client";

const client = new SentinelClient({
  baseUrl: "https://sentinel.your-domain.com",
  apiKey: "YOUR_API_KEY",
});

async function analyzeInput(text: string) {
  const result = await client.analyze(text);

  if (result.isSafe) {
    console.log("✅ Safe to proceed");
    return true;
  } else {
    console.log(`⛔ Blocked: ${result.reason}`);
    return false;
  }
}
```

### React Hook

```typescript
import { useSentinel } from "@sentinel-ai/react";

function ChatInput() {
  const { analyze, isLoading, error } = useSentinel();
  const [message, setMessage] = useState("");

  const handleSubmit = async () => {
    const result = await analyze(message);

    if (result.isSafe) {
      sendMessage(message);
    } else {
      alert("Message blocked for security reasons");
    }
  };

  return (
    <div>
      <input value={message} onChange={(e) => setMessage(e.target.value)} />
      <button onClick={handleSubmit} disabled={isLoading}>
        Send
      </button>
    </div>
  );
}
```

---

## OpenAI Integration

### Drop-in Proxy

```python
from openai import OpenAI

# Use SENTINEL instead of api.openai.com
client = OpenAI(
    base_url="https://sentinel.your-domain.com/v1",
    api_key="YOUR_SENTINEL_API_KEY"
)

response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ]
)

# SENTINEL automatically:
# 1. Checks incoming message
# 2. If safe — forwards to OpenAI
# 3. Checks response
# 4. Returns result
```

### Configuration

```env
PROXY_MODE=true
PROXY_TARGET_URL=https://api.openai.com/v1
PROXY_TARGET_API_KEY=sk-your-openai-key
PROXY_BLOCK_RESPONSE=generic
```

---

## LangChain Integration

### Callback Handler

```python
from langchain.callbacks.base import BaseCallbackHandler
from sentinel import SentinelClient

class SentinelCallbackHandler(BaseCallbackHandler):
    def __init__(self, sentinel_client: SentinelClient):
        self.client = sentinel_client

    def on_llm_start(self, serialized, prompts, **kwargs):
        for prompt in prompts:
            result = self.client.analyze(prompt)
            if not result.is_safe:
                raise ValueError(f"Blocked: {result.reason}")

    def on_llm_end(self, response, **kwargs):
        for generation in response.generations:
            for gen in generation:
                result = self.client.analyze_output(gen.text)
                if not result.is_safe:
                    gen.text = "[Response filtered]"

# Usage
sentinel = SentinelClient(api_key="YOUR_API_KEY")
handler = SentinelCallbackHandler(sentinel)

llm = ChatOpenAI(model="gpt-4", callbacks=[handler])
```

---

## Ollama Integration

```python
import requests
from sentinel import SentinelClient

sentinel = SentinelClient(
    base_url="https://sentinel.your-domain.com",
    api_key="YOUR_API_KEY"
)

def chat_with_ollama(prompt: str) -> str:
    # 1. Check incoming prompt
    input_result = sentinel.analyze(prompt)
    if not input_result.is_safe:
        return f"Blocked: {input_result.reason}"

    # 2. Send to Ollama
    response = requests.post("http://localhost:11434/api/generate", json={
        "model": "llama2",
        "prompt": prompt,
        "stream": False
    })
    llm_response = response.json()["response"]

    # 3. Check response
    output_result = sentinel.analyze_output(llm_response)
    return llm_response if output_result.is_safe else "Filtered."
```

---

## Webhook Integration

### Configuration

```env
WEBHOOK_ENABLED=true
WEBHOOK_URL=https://your-app.com/sentinel-webhook
WEBHOOK_SECRET=your-webhook-secret
```

### Webhook Format

```json
{
  "event": "analysis_completed",
  "timestamp": "2024-12-12T10:30:00.000Z",
  "data": {
    "request_id": "req-abc123",
    "risk_score": 0.85,
    "verdict": "HIGH_RISK",
    "engines_triggered": ["injection", "behavioral"]
  },
  "signature": "sha256=..."
}
```

### Handler (Python/Flask)

```python
from flask import Flask, request
import hmac
import hashlib

@app.route("/sentinel-webhook", methods=["POST"])
def handle_webhook():
    signature = request.headers.get("X-Sentinel-Signature")
    if not verify_signature(request.data, signature):
        return {"error": "Invalid signature"}, 401

    event = request.json

    if event["event"] == "analysis_completed":
        data = event["data"]
        if data["verdict"] == "BLOCKED":
            log_blocked_request(data)
            if data["risk_score"] > 0.9:
                notify_admin(data)

    return {"status": "ok"}
```

---

## Usage Examples

### 1. Moderated Chatbot

```python
from sentinel import SentinelClient
from openai import OpenAI

sentinel = SentinelClient(api_key="SENTINEL_KEY")
openai_client = OpenAI(api_key="OPENAI_KEY")

def moderated_chat(user_message: str, history: list) -> str:
    check = sentinel.analyze(text=user_message, context={"history": history})

    if not check.is_safe:
        return "I can't respond to that message."

    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=history + [{"role": "user", "content": user_message}]
    )

    return response.choices[0].message.content
```

### 2. Protected RAG System

```python
def protected_rag_query(query: str) -> str:
    # 1. Check query
    if not sentinel.analyze(query).is_safe:
        return "Invalid query."

    # 2. Get documents
    docs = vectorstore.similarity_search(query, k=5)

    # 3. Check documents for poisoning
    safe_docs = [d for d in docs if sentinel.analyze(d.page_content).is_safe]

    # 4. Generate and check response
    response = generate_answer(query, safe_docs)
    return response if sentinel.analyze_output(response).is_safe else "Cannot answer."
```

### 3. FastAPI Middleware

```python
from fastapi import FastAPI, Request, HTTPException
from sentinel import SentinelClient

app = FastAPI()
sentinel = SentinelClient(api_key="SENTINEL_KEY")

@app.middleware("http")
async def sentinel_middleware(request: Request, call_next):
    if request.method in ["POST", "PUT"]:
        body = await request.body()
        if body:
            result = sentinel.analyze(body.decode())
            if not result.is_safe:
                raise HTTPException(status_code=403, detail="Blocked")

    return await call_next(request)
```

---

**Integration complete! 🎉**

For more details, see the [Engine Reference](../reference/engines-en.md).
