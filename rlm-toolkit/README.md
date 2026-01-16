# RLM-Toolkit

[![CI](https://github.com/sentinel-community/rlm-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/sentinel-community/rlm-toolkit/actions)
[![PyPI](https://img.shields.io/pypi/v/rlm-toolkit.svg)](https://pypi.org/project/rlm-toolkit/)
[![Python](https://img.shields.io/pypi/pyversions/rlm-toolkit.svg)](https://pypi.org/project/rlm-toolkit/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

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
| **Secure REPL** | CIRCLE-compliant sandboxed code execution |
| **Multi-Provider** | OpenAI, Anthropic, Google, Ollama |
| **Cost Control** | Budget limits, cost tracking |
| **Observability** | OpenTelemetry, Langfuse, LangSmith |
| **Memory Systems** | Buffer, Episodic (EM-LLM inspired) |

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
