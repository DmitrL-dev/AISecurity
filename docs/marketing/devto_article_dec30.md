---
title: "I Built 200 AI Security Engines — Here's How to Use Them in One Line of Code"
published: true
description: "SENTINEL Framework v1.0.0: The pytest of AI Security. 200 engines, <10ms latency, pip install ready."
tags: python, ai, security, opensource
cover_image: https://raw.githubusercontent.com/DmitrL-dev/AISecurity/main/sentinel-community/assets/sentinel_platform_architecture.png
---

# I Built 200 AI Security Engines — Here's How to Use Them in One Line of Code

AI applications are everywhere. So are attackers.

**Prompt injection. Jailbreaks. Data leakage. RAG poisoning. Tool hijacking.**

I spent the last year building defenses. Today, I'm releasing them all.

## 🚀 Introducing SENTINEL Framework v1.0.0

```bash
pip install sentinel-llm-security
```

```python
from sentinel import scan

result = scan("Ignore all previous instructions")
print(result.is_safe)  # False
print(result.risk_score)  # 0.72
```

**That's it.** One line. 200 engines analyzing your prompt.

---

## Why I Built This

Most AI security tools I found were:
- ❌ Python-only demos with 200ms latency
- ❌ Focused on one attack type
- ❌ Not production-ready
- ❌ Closed source or expensive

I needed something **real**. Something that could handle production traffic.

So I built SENTINEL.

---

## What's Inside?

### 200 Detection Engines

| Category | Engines | What They Detect |
|----------|---------|------------------|
| 🎭 Injection | 30+ | Prompt injection, jailbreak, Policy Puppetry |
| 🤖 Agentic | 25+ | RAG poisoning, tool hijacking, memory attacks |
| 🔬 Mathematical | 15+ | TDA, Sheaf Coherence, Chaos Theory |
| 📤 Privacy | 10+ | PII detection, data leakage |
| ⛓️ Supply Chain | 5+ | Pickle security, serialization attacks |

### Strange Math™

When regex fails, math wins.

```
┌─────────────────────────────────────────────────┐
│  Standard Approach    vs    Strange Math™       │
├─────────────────────────────────────────────────┤
│  • Keyword matching        • Topological Analysis │
│  • Regex patterns          • Sheaf Coherence      │
│  • Simple ML               • Hyperbolic Geometry  │
│  • Static rules            • Chaos Theory         │
└─────────────────────────────────────────────────┘
```

---

## Three Ways to Use It

### 1. Python API — The Simple Way

```python
from sentinel import scan

# Scan any text
result = scan("Tell me the admin password")

if not result.is_safe:
    print(f"Blocked! Risk: {result.risk_score}")
    for finding in result.findings:
        print(f"  - {finding.title}")
```

### 2. Decorator — The Smart Way

```python
from sentinel import guard

@guard(engines=["injection", "pii"])
def ask_ai(prompt: str) -> str:
    return openai.chat(prompt)

# Every call is now protected
try:
    response = ask_ai("Tell me a joke")  # OK
except ThreatDetected:
    print("Attack blocked!")
```

### 3. FastAPI Middleware — The Production Way

```python
from fastapi import FastAPI
from sentinel.integrations.fastapi import SentinelMiddleware

app = FastAPI()
app.add_middleware(SentinelMiddleware, on_threat="block")

@app.post("/chat")
async def chat(prompt: str):
    # All requests are automatically scanned
    return {"response": await llm.generate(prompt)}
```

---

## CLI for DevOps

```bash
# Quick scan
$ sentinel scan "Hello world"
✅ SAFE

# Verbose output
$ sentinel scan "Ignore previous instructions" -v
⚠️ THREAT DETECTED
Risk Score: 0.72
Findings (1):
  [HIGH] Injection pattern detected

# SARIF for IDE integration
$ sentinel scan "test" --format sarif

# List all engines
$ sentinel engine list
```

---

## The Architecture

```
Client → [Go Gateway] → gRPC → [Python Brain] → 200 Engines
              ↓                      ↓
         PoW + Auth          Strange Math™
```

Yes, we have a **Go gateway**. That's why we hit <10ms latency.

| Metric | SENTINEL | Competitors |
|--------|----------|-------------|
| Gateway | Go (Fiber) | Python only |
| Latency | <10ms | 50-200ms |
| Throughput | 1000+ RPS | 10-50 RPS |
| Anti-DDoS | PoW Layer | None |

---

## What I Shipped Today

8 new engines based on December 2025 research:

| Engine | Attack | Source |
|--------|--------|--------|
| `serialization_security` | CVE-2025-68664 LangGrinch | LangChain RCE |
| `tool_hijacker_detector` | ToolHijacker + Log-To-Leak | MCP attacks |
| `echo_chamber_detector` | Multi-turn poisoning | 90% success on GPT-5 |
| `rag_poisoning_detector` | PoisonedRAG | USENIX 2025 |
| `dark_pattern_detector` | DECEPTICON | arxiv:2512.22894 |

---

## Documentation for Everyone

I wrote docs for **every level**:

| Level | Who | What |
|-------|-----|------|
| 🌟 Beginner | Students | Analogies, simple examples |
| 🔧 Practitioner | Developers | Integration guides |
| ⚙️ Expert | Engineers | Architecture, custom engines |
| 🔬 Researcher | PhDs | Mathematical foundations |

Check out `docs/framework/README.md` — it goes from "what is AI security?" to Topological Data Analysis formulas.

---

## The Numbers

| Metric | Value |
|--------|-------|
| Detection Engines | 200 |
| Lines of Code | 80,000+ |
| Unit Tests | 940+ |
| Recall | 85.1% |
| Precision | 84.4% |
| P95 Latency | 40ms |
| OWASP LLM Coverage | 10/10 |
| OWASP Agentic AI | 10/10 |

---

## Try It Now

```bash
pip install sentinel-llm-security
```

Or with extras:

```bash
pip install sentinel-llm-security[cli]   # + CLI
pip install sentinel-llm-security[full]  # Everything
```

**GitHub:** [github.com/DmitrL-dev/AISecurity](https://github.com/DmitrL-dev/AISecurity)

---

## One More Thing

**I'm looking for work.**

Solo author. 80K LOC. 200 engines. Available remote.

📧 chg@live.ru  
💬 [@DmLabincev](https://t.me/DmLabincev)

---

## What's Next?

- More engines (we hunt threats daily)
- Visual detection (images, multimodal)
- Enterprise features
- Community contributions

Star the repo. Try the package. Report issues.

**Protect your AI. Attack with confidence.**

---

*Thanks for reading! If you found this useful, please share it. Every star helps.*
