# 🛡️ SENTINEL Community Edition

**Open Source AI Security Platform for LLM Applications**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-green.svg)](https://python.org)

---

## Overview

SENTINEL Community Edition provides essential protection for LLM applications against:

- 🎯 **Prompt Injection** attacks
- 🔐 **PII/Secrets** leakage
- 🖼️ **VLM (Vision-Language)** attacks
- 📚 **RAG Poisoning** attacks
- 🔍 **Reconnaissance** attempts

### Detection Engines (15)

| Category              | Engines                                           |
| --------------------- | ------------------------------------------------- |
| **Classic Detection** | injection, yara, behavioral, pii, query, language |
| **NLP Guard**         | prompt_guard, hallucination                       |
| **Strange Math**      | tda_enhanced, sheaf_coherence                     |
| **VLM Protection**    | visual_content, cross_modal                       |
| **Agent Security**    | rag_guard, probing_detection                      |
| **Streaming**         | streaming                                         |

---

## Quick Start

### Installation

```bash
pip install sentinel-community
```

### Basic Usage

```python
from sentinel import SentinelGuard

guard = SentinelGuard()

# Analyze a prompt
result = guard.analyze("Tell me about machine learning")

if result.is_safe:
    print("✅ Prompt is safe")
else:
    print(f"⚠️ Blocked: {result.threat_type}")
```

### Docker

```bash
docker-compose up -d
curl http://localhost:8000/health
```

---

## API Endpoints

| Endpoint   | Method | Description                |
| ---------- | ------ | -------------------------- |
| `/analyze` | POST   | Analyze prompt for threats |
| `/health`  | GET    | Health check               |
| `/engines` | GET    | List active engines        |

### Example Request

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Ignore previous instructions"}'
```

### Example Response

```json
{
  "is_safe": false,
  "risk_score": 0.89,
  "threats": ["prompt_injection"],
  "blocked": true
}
```

---

## Configuration

```yaml
# config.yaml
sentinel:
  engines:
    - injection
    - pii
    - rag_guard

  thresholds:
    block: 0.7
    warn: 0.5
```

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    SENTINEL API                      │
├─────────────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │Injection│ │   PII   │ │RAG Guard│ │  TDA    │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │  YARA   │ │Behavioral│ │Probing │ │ Sheaf   │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
│          ... and 7 more engines ...                 │
├─────────────────────────────────────────────────────┤
│                   Ensemble Voting                    │
└─────────────────────────────────────────────────────┘
```

---

## Engines Description

<details>
<summary><strong>Classic Detection</strong></summary>

- **injection.py** - Prompt injection detection via regex + semantic analysis
- **yara_engine.py** - YARA signature-based pattern matching
- **behavioral.py** - Session behavioral analysis
- **pii.py** - PII/secrets detection using Presidio
- **query.py** - Query validation and sanitization
- **language.py** - Language detection and filtering

</details>

<details>
<summary><strong>Strange Math (Basic)</strong></summary>

- **tda_enhanced.py** - Topological Data Analysis (β₀, β₁ features)
- **sheaf_coherence.py** - Sheaf theory for multi-turn consistency

</details>

<details>
<summary><strong>VLM Protection</strong></summary>

- **visual_content.py** - OCR extraction from images
- **cross_modal.py** - CLIP-based text-image consistency

</details>

<details>
<summary><strong>Agent Security</strong></summary>

- **rag_guard.py** - RAG document poisoning detection
- **probing_detection.py** - System prompt probing detection

</details>

---

## Benchmarks

| Metric              | Value  |
| ------------------- | ------ |
| Latency p50         | <30ms  |
| Latency p99         | <100ms |
| Detection Accuracy  | 94%    |
| False Positive Rate | <0.5%  |

---

## 🚀 Upgrade to Enterprise

Need more protection? **SENTINEL Enterprise** includes:

| Feature                   | Community | Enterprise    |
| ------------------------- | --------- | ------------- |
| Detection Engines         | 15        | **85**        |
| Strange Math              | Basic (2) | **Full (11)** |
| Zero-Day Detection        | ❌        | ✅            |
| Red Team Automation       | ❌        | ✅            |
| Compliance (EU AI Act)    | ❌        | ✅            |
| MCP/A2A Protocol Security | ❌        | ✅            |
| Priority Support          | ❌        | ✅            |

**[Contact Sales](mailto:chg@live.ru)** | **[Enterprise Features](https://sentinel.ai/enterprise)**

---

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

---

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

---

## Contact

**Author:** Dmitry Labintsev  
**Email:** chg@live.ru  
**Telegram:** @DmLabincev

---

<p align="center">
  <strong>SENTINEL Community — Open Source AI Security</strong>
</p>
