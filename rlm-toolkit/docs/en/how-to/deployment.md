# How-to: Deployment

Recipes for deploying RLM applications to production.

## FastAPI Server

```python
from fastapi import FastAPI
from pydantic import BaseModel
from rlm_toolkit import RLM

app = FastAPI()
rlm = RLM.from_openai("gpt-4o")

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    response = rlm.run(request.message)
    return ChatResponse(response=response)

# Run: uvicorn main:app --host 0.0.0.0 --port 8000
```

## Streaming Endpoint

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()
rlm = RLM.from_openai("gpt-4o")

@app.get("/stream")
async def stream(query: str):
    async def generate():
        async for chunk in rlm.astream(query):
            yield f"data: {chunk}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )
```

## Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  rlm-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./data:/app/data
```

## Load Balancing

```python
from rlm_toolkit import RLM
from rlm_toolkit.providers import LoadBalancer

balancer = LoadBalancer([
    RLM.from_openai("gpt-4o"),
    RLM.from_openai("gpt-4o"),
    RLM.from_openai("gpt-4o")
], strategy="round_robin")

# Distribute load across instances
response = balancer.run("Hello")
```

## Rate Limiting

```python
from rlm_toolkit.middleware import RateLimiter

limiter = RateLimiter(
    requests_per_minute=60,
    tokens_per_minute=100000
)

rlm = RLM.from_openai("gpt-4o", middleware=[limiter])
```

## Health Check

```python
@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/ready")
async def ready():
    try:
        # Test LLM connection
        rlm.run("ping")
        return {"status": "ready"}
    except Exception as e:
        return {"status": "not ready", "error": str(e)}
```

## Kubernetes Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rlm-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rlm-api
  template:
    metadata:
      labels:
        app: rlm-api
    spec:
      containers:
      - name: rlm-api
        image: your-registry/rlm-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: llm-secrets
              key: openai-key
```

## Monitoring

```python
from rlm_toolkit.callbacks import PrometheusCallback

callback = PrometheusCallback(
    port=9090,
    metrics=["latency", "tokens", "errors"]
)

rlm = RLM.from_openai("gpt-4o", callbacks=[callback])
```

## Related

- [How-to: Callbacks](./callbacks.md)
- [How-to: Caching](./caching.md)
