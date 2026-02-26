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
from sentinel import scan, guard

# Simple scan
result = scan("Tell me about AI")
print(result.is_safe)  # True
print(result.risk_score)  # 0.15

# With specific engines
result = scan(
    "Hello",
    engines=["injection", "pii"]
)

# Decorator protection
@guard(engines=["injection", "pii"])
def my_llm_function(prompt: str) -> str:
    return call_llm(prompt)
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

---

## Compliance Endpoints

### GET /compliance/coverage

Get coverage summary for all compliance frameworks.

**Response:**

```json
{
  "frameworks": {
    "owasp_llm_top_10": {"covered": 10, "total": 10, "percent": 100},
    "owasp_agentic_ai": {"covered": 10, "total": 10, "percent": 100},
    "eu_ai_act": {"covered": 7, "total": 10, "percent": 70},
    "nist_ai_rmf": {"covered": 8, "total": 10, "percent": 80}
  }
}
```

### POST /compliance/report

Generate compliance report.

**Request:**

```json
{
  "frameworks": ["owasp_llm", "eu_ai_act"],
  "format": "pdf",
  "date_range": {"from": "2026-01-01", "to": "2026-01-31"}
}
```

---

## Requirements Endpoints

### POST /requirements/sets

Create custom security requirement set.

### GET /requirements/sets/{id}

Get requirements by ID.

### POST /requirements/sets/{id}/check

Check text against requirement set.

---

## Design Review Endpoints

### POST /design-review/documents

Analyze architecture documents for AI security risks.

**Request:**

```json
{
  "content": "## Architecture\nOur system uses RAG with external documents...",
  "format": "markdown"
}
```

**Response:**

```json
{
  "risks": [
    {
      "category": "rag_poisoning",
      "severity": "high",
      "owasp": "LLM03",
      "description": "External documents may contain hidden instructions"
    }
  ]
}
```
