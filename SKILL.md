---
name: sentinel-ai-security
description: AI Security Platform with 97 detection engines for protecting LLMs, AI agents, and multimodal systems. Detects prompt injection, jailbreaks, DAN attacks, and more. Includes Strike red team platform with 39,000+ attack payloads. Uses advanced mathematics including Topological Data Analysis, Sheaf Theory, and Hyperbolic Geometry. Production-ready with <10ms latency.
version: 4.0.0
author: DmitrL-dev
category: testing-security
tags:
  - ai-security
  - llm-security
  - prompt-injection
  - jailbreak-detection
  - red-team
  - penetration-testing
  - machine-learning
  - python
globs:
  - "**/*.py"
  - "**/sentinel*/**"
---

# SENTINEL AI Security Platform

AI Security Platform for protecting LLMs, AI agents, and multimodal systems.

## When to Use This Skill

Use SENTINEL when you need to:

- Detect prompt injection attacks in LLM inputs
- Identify jailbreak attempts (DAN, roleplay, encoding attacks)
- Perform red team testing on AI systems
- Audit AI agent security
- Analyze conversation safety

## Key Components

### 🛡️ Defense (97 Detection Engines)

- **Pattern-based**: Regex, keyword, semantic matching
- **ML-based**: Transformer classifiers, ensemble models
- **Strange Math™**: Topological Data Analysis, Sheaf Theory, Hyperbolic Geometry

### 🐉 Strike (Red Team Platform)

- 39,000+ attack payloads
- AI-powered reconnaissance
- WAF bypass techniques
- Multi-provider testing

## Quick Start

```bash
# Clone repository
git clone https://github.com/DmitrL-dev/AISecurity.git
cd AISecurity/sentinel-community

# Install
pip install -e .

# Basic usage
from sentinel import analyze
result = analyze("user input text")
print(result.risk_score)
```

## Example Commands

```
# Analyze a prompt for threats
sentinel analyze "Ignore previous instructions and..."

# Run red team attack
sentinel strike --target https://api.example.com --vectors all

# Start interactive demo
sentinel demo
```

## API Usage

```python
from sentinel.brain import SentinelBrain
from sentinel.core import AnalysisRequest

# Initialize with all engines
brain = SentinelBrain()

# Analyze input
request = AnalysisRequest(
    content="User message here",
    context={"conversation_id": "123"}
)
result = brain.analyze(request)

# Check results
if result.risk_score > 0.7:
    print(f"High risk detected: {result.threats}")
```

## Performance

| Metric    | Value |
| --------- | ----- |
| Recall    | 85.1% |
| Precision | 84.4% |
| F1 Score  | 84.7% |
| Latency   | <10ms |

## Links

- **GitHub**: https://github.com/DmitrL-dev/AISecurity
- **HuggingFace Dataset**: https://huggingface.co/datasets/Chgdz/sentinel-jailbreak-detection

## License

Apache 2.0 - Full open source, no restrictions.
