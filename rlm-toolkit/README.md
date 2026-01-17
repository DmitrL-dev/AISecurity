# RLM-Toolkit

[![CI](https://github.com/sentinel-community/rlm-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/sentinel-community/rlm-toolkit/actions)
[![PyPI](https://img.shields.io/pypi/v/rlm-toolkit.svg)](https://pypi.org/project/rlm-toolkit/)
[![Python](https://img.shields.io/pypi/pyversions/rlm-toolkit.svg)](https://pypi.org/project/rlm-toolkit/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Integrations](https://img.shields.io/badge/integrations-287%2B-brightgreen.svg)](docs/INTEGRATIONS.md)

**Recursive Language Models Toolkit** — библиотека для обработки контекстов произвольной длины (10M+ токенов) с использованием рекурсивных вызовов LLM.

## 🚀 Quick Start

```bash
pip install rlm-toolkit
```

```python
from rlm_toolkit import RLM

# Simple usage with Ollama
rlm = RLM.from_ollama("llama3")
result = rlm.run(
    context=open("large_document.txt").read(),
    query="What are the key findings?"
)
print(result.answer)
```

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Infinite Context** | Process 10M+ tokens with O(1) memory |
| **InfiniRetri** | 🆕 Attention-based retrieval, 100% accuracy on 1M+ tokens |
| **H-MEM** | 🆕 4-level hierarchical memory with LLM consolidation |
| **Self-Evolving** | 🆕 LLMs that improve through usage (R-Zero pattern) |
| **Multi-Agent** | 🆕 Decentralized P2P agents with Trust Zones |
| **DSPy Optimization** | 🆕 Automatic prompt optimization |
| **Secure REPL** | CIRCLE-compliant sandboxed code execution |
| **Multi-Provider** | 75 LLM providers (OpenAI, Anthropic, Google, Ollama, vLLM...) |
| **Document Loaders** | 135+ sources (Slack, Jira, GitHub, S3, databases...) |
| **Vector Stores** | 20+ stores (Pinecone, Chroma, Weaviate, pgvector...) |
| **Embeddings** | 15+ providers (OpenAI, BGE, E5, Jina, Cohere...) |
| **Cost Control** | Budget limits, cost tracking |
| **Observability** | OpenTelemetry, Langfuse, LangSmith, W&B (12 backends) |
| **Memory Systems** | Buffer, Episodic, Hierarchical (H-MEM) |

> 📋 **[Full Integration Catalog](docs/INTEGRATIONS.md)** — 287+ production-ready integrations

## 🔥 InfiniRetri (NEW)

Attention-based infinite context retrieval — 100% accuracy on Needle-In-a-Haystack up to 1M+ tokens.

```python
from rlm_toolkit.retrieval import InfiniRetriever

# Retrieve from 1M+ token documents
retriever = InfiniRetriever("Qwen/Qwen2.5-0.5B-Instruct")
answer = retriever.retrieve(
    context=million_token_doc,
    question="What is the secret code?"
)

# Or use automatic routing in RLM
from rlm_toolkit import RLM, RLMConfig

config = RLMConfig(
    use_infiniretri=True,
    infiniretri_threshold=100_000,  # Auto-switch at 100K tokens
)
rlm = RLM.from_ollama("llama3", config=config)
result = rlm.run(huge_document, "Summarize")  # Automatically uses InfiniRetri
```

> Based on [arXiv:2502.12962](https://arxiv.org/abs/2502.12962) — requires `pip install infini-retri`

## 🧠 Hierarchical Memory (H-MEM) (NEW)

Multi-level persistent memory with semantic consolidation — memories that learn and evolve.

```python
from rlm_toolkit.memory import HierarchicalMemory, SecureHierarchicalMemory

# Basic H-MEM
hmem = HierarchicalMemory()
hmem.add_episode("User asked about weather")
hmem.add_episode("AI responded with forecast")
hmem.consolidate()  # Auto-creates traces, categories, domains

results = hmem.retrieve("weather")

# Secure H-MEM with encryption and trust zones
smem = SecureHierarchicalMemory(
    agent_id="agent-001",
    trust_zone="zone-secure"
)
smem.add_episode("Confidential data")
smem.grant_access("agent-002", "zone-secure")
```

**4-Level Architecture:**
```
Level 3: DOMAIN    → High-level knowledge
Level 2: CATEGORY  → Semantic categories  
Level 1: TRACE     → Consolidated memories
Level 0: EPISODE   → Raw interactions
```

> Based on arXiv H-MEM paper (July 2025)

## 🧬 Self-Evolving LLMs (NEW)

LLMs that improve reasoning through usage — no human supervision required.

```python
from rlm_toolkit.evolve import SelfEvolvingRLM, EvolutionStrategy
from rlm_toolkit.providers import OllamaProvider

# Create self-evolving RLM
evolve = SelfEvolvingRLM(
    provider=OllamaProvider("llama3"),
    strategy=EvolutionStrategy.CHALLENGER_SOLVER
)

# Solve with self-refinement
answer = evolve.solve("What is 25 * 17?")
print(f"Answer: {answer.answer}, Confidence: {answer.confidence}")

# Run training loop (generates challenges → solves → improves)
metrics = evolve.training_loop(iterations=10, domain="math")
print(f"Success rate: {metrics.success_rate}")
```

**Strategies:**
- `SELF_REFINE` — Iterative self-improvement
- `CHALLENGER_SOLVER` — R-Zero co-evolutionary loop
- `EXPERIENCE_REPLAY` — Learn from past solutions

> Based on R-Zero (arXiv:2508.05004)

## 🤖 Multi-Agent Framework (NEW)

Decentralized P2P agents inspired by Meta Matrix — no central orchestrator bottleneck.

```python
from rlm_toolkit.agents import MultiAgentRuntime, SecureAgent, EvolvingAgent

# Create runtime
runtime = MultiAgentRuntime()

# Register agents with Trust Zones
runtime.register(SecureAgent("analyst", "Data Analyst", trust_zone="internal"))
runtime.register(EvolvingAgent("solver", "Problem Solver", llm_provider=provider))

# Run message through agents
from rlm_toolkit.agents import AgentMessage
message = AgentMessage(content="Analyze this data", routing=["analyst", "solver"])
result = runtime.run(message)
```

**Agent Types:**
- `SecureAgent` — H-MEM Trust Zones integration
- `EvolvingAgent` — Self-improving via R-Zero
- `SecureEvolvingAgent` — Both combined

> Based on Meta Matrix (arXiv 2025)

## 🎯 DSPy-Style Optimization (NEW)

Automatic prompt optimization — define what, not how.

```python
from rlm_toolkit.optimize import Signature, Predict, ChainOfThought, BootstrapFewShot

# Define signature
sig = Signature(
    inputs=["question", "context"],
    outputs=["answer"],
    instructions="Answer based on context"
)

# Use with Chain of Thought
cot = ChainOfThought(sig, provider)
result = cot(question="What is X?", context="X is 42")

# Auto-optimize with few-shot selection
optimizer = BootstrapFewShot(metric=lambda p, g: p["answer"] == g["answer"])
optimized = optimizer.compile(Predict(sig, provider), trainset=examples)
```

**Modules:** `Predict`, `ChainOfThought`, `SelfRefine`  
**Optimizers:** `BootstrapFewShot`, `PromptOptimizer`

> Inspired by Stanford DSPy

## 📦 Installation

```bash
# Basic
pip install rlm-toolkit

# With all providers
pip install rlm-toolkit[all]

# Development
pip install -e ".[dev]"
```

## 🔧 Usage

### Basic

```python
from rlm_toolkit import RLM, RLMConfig

# With configuration
config = RLMConfig(
    max_iterations=50,
    max_cost=5.0,  # USD
)

rlm = RLM.from_openai("gpt-4o", config=config)
result = rlm.run(context, query)
```

### With Memory

```python
from rlm_toolkit.memory import EpisodicMemory

memory = EpisodicMemory(max_entries=1000)
rlm = RLM.from_ollama("llama3", memory=memory)

# Memory persists across runs
result1 = rlm.run(doc1, "Summarize this")
result2 = rlm.run(doc2, "Compare with previous")
```

### With Observability

```python
from rlm_toolkit.observability import Tracer, CostTracker

tracer = Tracer(service_name="my-app")
cost_tracker = CostTracker(budget=10.0)

rlm = RLM.from_openai("gpt-4o", tracer=tracer, cost_tracker=cost_tracker)
```

## 🔒 Security

RLM-Toolkit implements CIRCLE-compliant security:

- **AST Analysis** — Block dangerous imports before execution
- **Sandboxed REPL** — Isolated code execution with timeouts
- **Virtual Filesystem** — Quota-enforced file operations
- **Attack Detection** — Obfuscation and indirect attack patterns

```python
from rlm_toolkit import RLMConfig, SecurityConfig

config = RLMConfig(
    security=SecurityConfig(
        sandbox=True,
        max_execution_time=30.0,
        max_memory_mb=512,
    )
)
```

## 📊 Benchmarks

Based on RLM paper methodology:

| Benchmark | Score |
|-----------|-------|
| OOLONG-Pairs | TBD |
| CIRCLE Security | ~95% |

## 🛠️ CLI

```bash
# Run a query
rlm run --model ollama:llama3 --context file.txt --query "Summarize"

# Interactive REPL
rlm repl --model openai:gpt-4o

# Cost tracking
rlm trace --session latest
```

## 📚 Documentation

- [Getting Started](docs/getting_started.md)
- [API Reference](docs/api/index.md)
- [Security Guide](docs/security.md)
- [Examples](examples/)

## 🤝 Contributing

```bash
# Clone repo
git clone https://github.com/sentinel-community/rlm-toolkit.git
cd rlm-toolkit

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check rlm_toolkit/
```

## 📄 License

Apache 2.0 — see [LICENSE](LICENSE)

## 🙏 Acknowledgments

- [RLM Paper](https://arxiv.org/abs/2410.XXXXX) by Zhang, Kraska, Khattab
- [CIRCLE Benchmark](https://arxiv.org/abs/2507.19399)
- SENTINEL Community
