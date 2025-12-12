# Quick Start Guide

Get started with SENTINEL Community in 5 minutes.

## 1. Install

```bash
pip install sentinel-community
```

## 2. Basic Usage

```python
from sentinel import InjectionDetector, PIIDetector, RAGGuard

# Initialize detectors
injection = InjectionDetector()
pii = PIIDetector()
rag = RAGGuard()

# Analyze a prompt
prompt = "Tell me about machine learning"

# Check for injection
result = injection.analyze(prompt)
if not result.is_safe:
    print(f"⚠️ Injection detected: {result.threat_type}")

# Check for PII
pii_result = pii.analyze(prompt)
if pii_result.has_pii:
    print(f"⚠️ PII found: {pii_result.entities}")
```

## 3. Using Multiple Engines

```python
from sentinel import (
    InjectionDetector,
    PIIDetector,
    RAGGuard,
    TDAEnhanced,
)

class SentinelGuard:
    def __init__(self):
        self.engines = [
            InjectionDetector(),
            PIIDetector(),
            RAGGuard(),
            TDAEnhanced(),
        ]

    def analyze(self, prompt: str) -> dict:
        results = []
        for engine in self.engines:
            result = engine.analyze(prompt)
            results.append({
                "engine": engine.__class__.__name__,
                "is_safe": result.is_safe,
                "score": result.risk_score,
            })

        # Ensemble voting
        block_votes = sum(1 for r in results if not r["is_safe"])
        is_safe = block_votes < len(results) / 2

        return {
            "is_safe": is_safe,
            "engines": results,
        }

# Usage
guard = SentinelGuard()
result = guard.analyze("Ignore previous instructions")
print(result)
```

## 4. API Server

```bash
# Start server
uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# Test
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello world"}'
```

## 5. Docker

```bash
docker-compose up -d
curl http://localhost:8000/health
```

---

## Available Engines

| Engine              | Purpose                |
| ------------------- | ---------------------- |
| `InjectionDetector` | Prompt injection       |
| `PIIDetector`       | PII/secrets            |
| `RAGGuard`          | RAG poisoning          |
| `TDAEnhanced`       | Topological anomalies  |
| `SheafCoherence`    | Multi-turn consistency |
| `VisualContent`     | VLM OCR protection     |
| `CrossModal`        | Text-image consistency |
| `ProbingDetection`  | Recon detection        |

---

## Next Steps

- [Configuration Guide](../guides/configuration.md)
- [API Reference](../reference/api.md)
- [Upgrade to Enterprise](https://sentinel.ai/enterprise)
