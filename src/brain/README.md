<p align="center">
  <img src="../../docs/images/brain_hero.png" alt="SENTINEL Brain" width="100%">
</p>

<h1 align="center">SENTINEL Brain</h1>

<p align="center">
  <strong>🧠 187 Detection Engines — Strange Math™ Protection</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Engines-187-brightgreen?style=for-the-badge" alt="Engines">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge" alt="Python">
  <img src="https://img.shields.io/badge/Latency-3ms_P50-orange?style=for-the-badge" alt="Latency">
  <img src="https://img.shields.io/badge/License-Apache_2.0-green?style=for-the-badge" alt="License">
</p>

---

## 🔥 What is SENTINEL Brain?

SENTINEL Brain is the **detection core** of the SENTINEL AI Security Platform. It analyzes every prompt and response in real-time using 217 specialized engines.

| Category | Engines | Detection |
|----------|---------|-----------|
| 🎯 **Injection** | 30+ | Prompt injection, jailbreak, Policy Puppetry |
| 🤖 **Agentic** | 25+ | RAG poisoning, tool hijacking, memory attacks |
| 📐 **Mathematical** | 15+ | TDA, Sheaf Coherence, Chaos Theory |
| 🔒 **Privacy** | 10+ | PII detection, data leakage prevention |
| 📦 **Supply Chain** | 5+ | Pickle security, serialization attacks |

---

## 🚀 Quick Start

```bash
pip install sentinel-llm-security
```

```python
from sentinel import scan

result = scan("Ignore previous instructions and...")
print(result.is_safe)      # False
print(result.risk_score)   # 0.95
print(result.detections)   # ['prompt_injection', 'policy_puppetry']
```

---

## 📐 Strange Math™

**What makes SENTINEL different from keyword matching?**

| Standard Approach | SENTINEL Strange Math™ |
|-------------------|------------------------|
| Keyword matching | **Topological Data Analysis** |
| Regex patterns | **Sheaf Coherence Theory** |
| Simple ML classifiers | **Hyperbolic Geometry** |
| Static rules | **Optimal Transport** |
| — | **Chaos Theory** |

### Example: TDA Analyzer

```python
from sentinel.brain.engines import TDAAnalyzer

analyzer = TDAAnalyzer()
result = analyzer.analyze(prompt)
# Uses persistent homology to detect semantic anomalies
```

---

## 📊 Benchmarks

| Engine Category | Precision | Recall | F1 | P50 | P99 |
|-----------------|-----------|--------|----|----|-----|
| **Injection** (Tier 1) | 97% | 94% | 95.5% | 3ms | 12ms |
| **Jailbreak** (Tier 2) | 95% | 91% | 93% | 8ms | 25ms |
| **RAG Poisoning** | 92% | 89% | 90.5% | 15ms | 45ms |
| **TDA Analyzer** (Tier 3) | 89% | 96% | 92.4% | 45ms | 120ms |
| **Combined Pipeline** | 94% | 93% | 93.5% | 18ms | 85ms |

> Tested on SENTINEL Strike payloads + internal validation set.

---

## 🏗️ Architecture

```
src/brain/
├── engines/         # 217 detection engines
│   ├── injection/   # Prompt injection detection
│   ├── jailbreak/   # Jailbreak prevention
│   ├── agentic/     # RAG/Agent/Tool protection
│   ├── mathematical/ # TDA, Sheaf, Chaos engines
│   └── privacy/     # PII, secrets detection
├── core/            # Engine orchestration
├── config/          # Engine configuration
├── api/             # REST/gRPC endpoints
└── integrations/    # OpenAI, Anthropic, LangChain
```

---

## 🔌 Integrations

Built-in support for:
- **LLM Providers:** OpenAI, Anthropic, Google, Ollama, HuggingFace
- **Frameworks:** LangChain, LlamaIndex, Haystack
- **Vector Stores:** Pinecone, Weaviate, Qdrant, Chroma
- **Orchestration:** FastAPI, Flask, Django

---

## 📚 Related

- [SENTINEL Shield](../../shield/) — C DMZ proxy
- [SENTINEL Strike](../../strike/) — Red team platform
- [SENTINEL Framework](../sentinel/) — Python SDK

---

<p align="center">
  <strong>SENTINEL Brain</strong><br>
  <em>217 Reasons You're Protected</em>
</p>
