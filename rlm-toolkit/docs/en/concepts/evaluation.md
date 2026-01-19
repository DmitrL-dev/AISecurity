# Evaluation

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **Benchmarks and metrics** for RLM performance

## Quick Start

```python
from rlm_toolkit.evaluation import OOLONGBenchmark
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")
benchmark = OOLONGBenchmark()

results = benchmark.run(rlm)
print(f"Accuracy: {results.accuracy:.2%}")
```

## Benchmarks

### OOLONG (1M+ tokens)

```python
from rlm_toolkit.evaluation import OOLONGBenchmark

benchmark = OOLONGBenchmark(
    dataset_path="./oolong_dataset.json",
    max_samples=100
)

results = benchmark.run(rlm)
print(f"Accuracy: {results.accuracy:.2%}")
print(f"Avg latency: {results.avg_latency_ms}ms")
```

### Custom Benchmark

```python
from rlm_toolkit.evaluation import Benchmark, TestCase

cases = [
    TestCase(
        input="What is 2+2?",
        expected="4",
        metric="exact_match"
    ),
    TestCase(
        input="Capital of France?",
        expected="Paris",
        metric="contains"
    )
]

benchmark = Benchmark(test_cases=cases)
results = benchmark.run(rlm)
```

## Metrics

| Metric | Description |
|--------|-------------|
| `exact_match` | Exact string match |
| `contains` | Expected in response |
| `semantic` | Embedding similarity |
| `llm_judge` | LLM evaluates response |

```python
from rlm_toolkit.evaluation import SemanticMetric

metric = SemanticMetric(embeddings=OpenAIEmbeddings())
score = metric.score(prediction="The sky is blue", reference="Sky color is blue")
# 0.92
```

## CLI

```bash
rlm eval oolong --model openai:gpt-4o --report results.html
```

## Related

- [Observability](observability.md)
- [Optimize](optimize.md)
