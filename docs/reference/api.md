# API Reference

## Endpoints

### POST /analyze

Analyze a prompt for threats.

**Request:**

```json
{
  "prompt": "string",
  "context": ["string"], // optional
  "engines": ["injection", "pii"] // optional, defaults to all
}
```

**Response:**

```json
{
  "is_safe": true,
  "risk_score": 0.15,
  "threats": [],
  "blocked": false,
  "engines": [
    {
      "name": "injection",
      "is_safe": true,
      "score": 0.1
    },
    {
      "name": "pii",
      "is_safe": true,
      "score": 0.2
    }
  ],
  "processing_time_ms": 45
}
```

---

### GET /health

Health check endpoint.

**Response:**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "engines_loaded": 15
}
```

---

### GET /engines

List available engines.

**Response:**

```json
{
  "engines": [
    {
      "name": "injection",
      "enabled": true,
      "description": "Prompt injection detection"
    },
    {
      "name": "pii",
      "enabled": true,
      "description": "PII/secrets detection"
    }
  ]
}
```

---

## Python SDK

```python
from sentinel import SentinelClient

client = SentinelClient(base_url="http://localhost:8000")

# Analyze prompt
result = client.analyze("Tell me about AI")
print(result.is_safe)

# With specific engines
result = client.analyze(
    prompt="Hello",
    engines=["injection", "pii"]
)
```

---

## Error Codes

| Code | Description         |
| ---- | ------------------- |
| 200  | Success             |
| 400  | Invalid request     |
| 422  | Validation error    |
| 500  | Internal error      |
| 503  | Service unavailable |

---

## Rate Limits

| Plan       | Requests/min |
| ---------- | ------------ |
| Community  | 60           |
| Enterprise | Unlimited    |
