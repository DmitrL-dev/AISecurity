# Evaluation

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **Бенчмарки и метрики** для производительности RLM

## Быстрый старт

```python
from rlm_toolkit.evaluation import OOLONGBenchmark
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")
benchmark = OOLONGBenchmark()

results = benchmark.run(rlm)
print(f"Точность: {results.accuracy:.2%}")
```

## Бенчмарки

### OOLONG (1M+ токенов)

```python
from rlm_toolkit.evaluation import OOLONGBenchmark

benchmark = OOLONGBenchmark(
    dataset_path="./oolong_dataset.json",
    max_samples=100
)

results = benchmark.run(rlm)
print(f"Точность: {results.accuracy:.2%}")
print(f"Средняя латентность: {results.avg_latency_ms}ms")
```

### Кастомный бенчмарк

```python
from rlm_toolkit.evaluation import Benchmark, TestCase

cases = [
    TestCase(
        input="Сколько будет 2+2?",
        expected="4",
        metric="exact_match"
    ),
    TestCase(
        input="Столица Франции?",
        expected="Париж",
        metric="contains"
    )
]

benchmark = Benchmark(test_cases=cases)
results = benchmark.run(rlm)
```

## Метрики

| Метрика | Описание |
|---------|----------|
| `exact_match` | Точное совпадение строки |
| `contains` | Ожидаемое в ответе |
| `semantic` | Схожесть эмбеддингов |
| `llm_judge` | LLM оценивает ответ |

```python
from rlm_toolkit.evaluation import SemanticMetric

metric = SemanticMetric(embeddings=OpenAIEmbeddings())
score = metric.score(prediction="Небо голубое", reference="Цвет неба голубой")
# 0.92
```

## CLI

```bash
rlm eval oolong --model openai:gpt-4o --report results.html
```

## Связанное

- [Observability](observability.md)
- [Optimize](optimize.md)
