# Getting Started

This guide will help you get up and running with RLM-Toolkit in 5 minutes.

## Installation

```bash
pip install rlm-toolkit
```

## Prerequisites

- Python 3.10+
- One of: Ollama, OpenAI API key, Anthropic API key, Google API key

## Quick Example

```python
from rlm_toolkit import RLM

# Using local Ollama (no API key needed)
rlm = RLM.from_ollama("llama3")

# Load a large document
with open("report.txt") as f:
    document = f.read()

# Ask a question
result = rlm.run(
    context=document,
    query="What are the main conclusions?"
)

print(result.answer)
print(f"Cost: ${result.total_cost:.4f}")
print(f"Iterations: {result.iterations}")
```

## Providers

### Ollama (Local)

```bash
# Install Ollama first: https://ollama.ai
ollama pull llama3
```

```python
from rlm_toolkit import RLM
rlm = RLM.from_ollama("llama3")
```

### OpenAI

```bash
export OPENAI_API_KEY="sk-..."
```

```python
from rlm_toolkit import RLM
rlm = RLM.from_openai("gpt-4o")
```

### Anthropic

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

```python
from rlm_toolkit import RLM
rlm = RLM.from_anthropic("claude-3-opus")
```

## Configuration

```python
from rlm_toolkit import RLM, RLMConfig

config = RLMConfig(
    max_iterations=50,      # Max REPL iterations
    max_cost=10.0,          # Budget in USD
    timeout=600.0,          # Total timeout (seconds)
)

rlm = RLM.from_openai("gpt-4o", config=config)
```

## Security

RLM executes Python code in a sandboxed environment. By default:

- Dangerous imports (os, subprocess, socket) are blocked
- Execution timeout: 30 seconds
- Memory limit: 512 MB

```python
from rlm_toolkit import RLMConfig, SecurityConfig

config = RLMConfig(
    security=SecurityConfig(
        sandbox=True,
        max_execution_time=10.0,
        max_memory_mb=256,
    )
)
```

## Next Steps

- [API Reference](api/index.md)
- [Security Guide](security.md)
- [Examples](../examples/)
