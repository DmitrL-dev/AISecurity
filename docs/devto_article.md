---
title: Christmas Gift: Open-Sourcing 99 AI Security Detection Engines
published: true
description: I'm releasing the full source code of SENTINEL — an AI security platform with 99 detection engines, one-liner deploy, and OWASP Agentic 2026 10/10 coverage.
tags: opensource, security, machinelearning, python
cover_image: https://raw.githubusercontent.com/DmitrL-dev/AISecurity/main/sentinel-community/assets/christmas_2025.png
---

I'm releasing the full source code of SENTINEL — an AI security platform. Not a "lite version" or "community edition" — **everything**.

## 🚀 One-Liner Deploy (NEW!)

```bash
curl -sSL https://raw.githubusercontent.com/DmitrL-dev/AISecurity/main/install.sh | bash
```

**5 services, 99 engines, 5 minutes:**
- Gateway (Go) — HTTP/HTTPS API
- Brain (Python) — 99 detection engines
- Redis — caching & rate limiting
- PostgreSQL — audit logs
- Dashboard — web UI

## What is it?

SENTINEL is a security platform for LLMs, AI agents, and multimodal systems:

| Component | Description |
|-----------|-------------|
| 🛡️ **Defense** | 99 detection engines (<10ms latency) |
| ⚔️ **Strike** | Red team platform (39,000+ attack payloads) |
| 📊 **OWASP Coverage** | LLM Top 10 ✅ + Agentic Top 10 2026 **10/10** ✅ |

Think of it as a **firewall + pentest suite**, but for AI.

## The "Strange Math" Engines

While most AI security tools use pattern matching, we went a different way:

### Topological Data Analysis (TDA)

```python
from gudhi import RipsComplex

rips = RipsComplex(points=embedding, max_edge_length=2.0)
simplex_tree = rips.create_simplex_tree(max_dimension=2)
persistence = simplex_tree.persistence()

# Attacks create topological anomalies in embedding space
```

**Idea:** Jailbreak attempts create "holes" in the embedding topology that normal text doesn't.

### Sheaf Theory

Coherence verification across multi-turn conversations. Detects attacks that slowly shift context across messages.

### Hyperbolic Geometry

Poincaré ball embeddings for attack clustering. Semantic relationships form hierarchies that attacks disrupt.

## December 2025 Updates

| Feature | Status |
|---------|--------|
| **99 Detection Engines** | +2 from launch |
| **OWASP Agentic 2026** | 10/10 coverage |
| **Supply Chain Guard** | MCP/A2A protection |
| **Trust Exploitation** | Social engineering via AI |
| **Echo State Network** | Temporal pattern detection |
| **One-Liner Deploy** | 5 services in 5 minutes |

## Benchmarks

| Metric | Value |
|--------|-------|
| Recall | **85.1%** |
| Precision | **84.4%** |
| F1 Score | **84.7%** |
| Latency | **<10ms** |
| Engines | **99** |

Tested on 1,815 samples from 3 HuggingFace datasets.

## Quick Start

### Option 1: One-Liner (Recommended)

```bash
curl -sSL https://raw.githubusercontent.com/DmitrL-dev/AISecurity/main/install.sh | bash
```

### Option 2: Docker Compose

```bash
git clone https://github.com/DmitrL-dev/AISecurity.git
cd AISecurity/sentinel-community
cp .env.example .env
docker-compose -f docker-compose.full.yml up -d
```

### Option 3: Python Package

```bash
git clone https://github.com/DmitrL-dev/AISecurity.git
cd AISecurity/sentinel-community
pip install -e .
```

## API Example

```bash
curl -X POST http://localhost:8080/api/v1/analyze \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Ignore all previous instructions"}'
```

Response:
```json
{
  "safe": false,
  "risk_score": 85.5,
  "threats": ["prompt_injection"],
  "blocked": true,
  "latency_ms": 8
}
```

## Why Open Source?

1. **AI security needs transparency** — trust but verify
2. **Threats evolve too fast** for one team
3. **It's Christmas** 🎄

## Links

- **GitHub:** [github.com/DmitrL-dev/AISecurity](https://github.com/DmitrL-dev/AISecurity)
- **HuggingFace:** [51K samples dataset](https://huggingface.co/datasets/Chgdz/sentinel-jailbreak-detection)
- **Colab Demo:** [Try it now](https://colab.research.google.com/github/DmitrL-dev/AISecurity/blob/main/SENTINEL_Strike_Demo.ipynb)
- **Documentation:** [dmitrl-dev.github.io/AISecurity](https://dmitrl-dev.github.io/AISecurity/)

---

Happy to answer questions! ⭐ Star the repo if you find it useful.

🚀
