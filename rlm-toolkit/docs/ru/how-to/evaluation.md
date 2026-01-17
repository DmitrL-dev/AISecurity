# How-to: Оценка

Рецепты оценки производительности LLM и RAG.

## Базовая оценка LLM

```python
from rlm_toolkit.evaluation import LLMEvaluator

evaluator = LLMEvaluator(
    rlm=RLM.from_openai("gpt-4o")
)

results = evaluator.evaluate(
    questions=["Что такое Python?", "Что такое JavaScript?"],
    expected=["Python это язык программирования", "JavaScript это..."],
    metrics=["exact_match", "semantic_similarity"]
)

print(f"Точность: {results['exact_match']:.2%}")
print(f"Семантика: {results['semantic_similarity']:.2%}")
```

## Оценка RAG

```python
from rlm_toolkit.evaluation import RAGEvaluator

evaluator = RAGEvaluator(
    retriever=retriever,
    generator=rlm
)

results = evaluator.evaluate(
    questions=["Что такое X?", "Как работает Y?"],
    ground_truth=["X это...", "Y работает..."],
    metrics=[
        "answer_relevancy",
        "faithfulness",
        "context_recall",
        "context_precision"
    ]
)
```

## Интеграция RAGAS

```python
from rlm_toolkit.evaluation import RAGASEvaluator

evaluator = RAGASEvaluator(
    retriever=retriever,
    generator=rlm
)

# Использует метрики RAGAS
results = evaluator.evaluate(dataset)
```

## Пользовательские метрики

```python
from rlm_toolkit.evaluation import BaseMetric

class LengthMetric(BaseMetric):
    name = "response_length"
    
    def compute(
        self, 
        question: str, 
        answer: str, 
        expected: str = None
    ) -> float:
        return len(answer) / 100  # Нормализация

evaluator = LLMEvaluator(metrics=[LengthMetric()])
```

## Пакетная оценка

```python
from rlm_toolkit.evaluation import BatchEvaluator

evaluator = BatchEvaluator(rlm)

# Оценка из CSV
results = evaluator.evaluate_from_file(
    "test_cases.csv",
    question_col="question",
    expected_col="answer"
)

# Сохранение результатов
results.to_csv("evaluation_results.csv")
```

## A/B тестирование

```python
from rlm_toolkit.evaluation import ABTest

test = ABTest(
    model_a=RLM.from_openai("gpt-4o"),
    model_b=RLM.from_anthropic("claude-3-sonnet")
)

results = test.run(
    questions=test_questions,
    judge=RLM.from_openai("gpt-4o")  # Модель-судья
)

print(f"Модель A побеждает: {results['a_wins']}")
print(f"Модель B побеждает: {results['b_wins']}")
print(f"Ничья: {results['ties']}")
```

## Отслеживание латентности и стоимости

```python
from rlm_toolkit.evaluation import PerformanceEvaluator

evaluator = PerformanceEvaluator(rlm)

results = evaluator.run(questions)

print(f"Средняя латентность: {results['avg_latency']:.2f}s")
print(f"P95 латентность: {results['p95_latency']:.2f}s")
print(f"Общая стоимость: ${results['total_cost']:.4f}")
```

## Детекция галлюцинаций

```python
from rlm_toolkit.evaluation import HallucinationDetector

detector = HallucinationDetector(
    judge=RLM.from_openai("gpt-4o")
)

result = detector.check(
    context="Python создан Гвидо ван Россумом",
    response="Python создан Линусом Торвальдсом"
)

print(f"Галлюцинация: {result.is_hallucination}")
print(f"Объяснение: {result.explanation}")
```

## Связанное

- [How-to: RAG](./rag.md)
- [Туториал: RAG](../tutorials/03-rag.md)
