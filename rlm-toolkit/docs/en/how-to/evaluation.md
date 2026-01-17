# How-to: Evaluation

Recipes for evaluating LLM and RAG performance.

## Basic LLM Evaluation

```python
from rlm_toolkit.evaluation import LLMEvaluator

evaluator = LLMEvaluator(
    rlm=RLM.from_openai("gpt-4o")
)

results = evaluator.evaluate(
    questions=["What is Python?", "What is JavaScript?"],
    expected=["Python is a programming language", "JavaScript is..."],
    metrics=["exact_match", "semantic_similarity"]
)

print(f"Accuracy: {results['exact_match']:.2%}")
print(f"Semantic: {results['semantic_similarity']:.2%}")
```

## RAG Evaluation

```python
from rlm_toolkit.evaluation import RAGEvaluator

evaluator = RAGEvaluator(
    retriever=retriever,
    generator=rlm
)

results = evaluator.evaluate(
    questions=["What is X?", "How does Y work?"],
    ground_truth=["X is...", "Y works by..."],
    metrics=[
        "answer_relevancy",
        "faithfulness",
        "context_recall",
        "context_precision"
    ]
)
```

## RAGAS Integration

```python
from rlm_toolkit.evaluation import RAGASEvaluator

evaluator = RAGASEvaluator(
    retriever=retriever,
    generator=rlm
)

# Uses RAGAS metrics
results = evaluator.evaluate(dataset)
```

## Custom Metrics

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
        return len(answer) / 100  # Normalize

evaluator = LLMEvaluator(metrics=[LengthMetric()])
```

## Batch Evaluation

```python
from rlm_toolkit.evaluation import BatchEvaluator

evaluator = BatchEvaluator(rlm)

# Evaluate from CSV
results = evaluator.evaluate_from_file(
    "test_cases.csv",
    question_col="question",
    expected_col="answer"
)

# Save results
results.to_csv("evaluation_results.csv")
```

## A/B Testing

```python
from rlm_toolkit.evaluation import ABTest

test = ABTest(
    model_a=RLM.from_openai("gpt-4o"),
    model_b=RLM.from_anthropic("claude-3-sonnet")
)

results = test.run(
    questions=test_questions,
    judge=RLM.from_openai("gpt-4o")  # Judge model
)

print(f"Model A wins: {results['a_wins']}")
print(f"Model B wins: {results['b_wins']}")
print(f"Ties: {results['ties']}")
```

## Latency and Cost Tracking

```python
from rlm_toolkit.evaluation import PerformanceEvaluator

evaluator = PerformanceEvaluator(rlm)

results = evaluator.run(questions)

print(f"Avg latency: {results['avg_latency']:.2f}s")
print(f"P95 latency: {results['p95_latency']:.2f}s")
print(f"Total cost: ${results['total_cost']:.4f}")
```

## Hallucination Detection

```python
from rlm_toolkit.evaluation import HallucinationDetector

detector = HallucinationDetector(
    judge=RLM.from_openai("gpt-4o")
)

result = detector.check(
    context="Python was created by Guido van Rossum",
    response="Python was created by Linus Torvalds"
)

print(f"Hallucination: {result.is_hallucination}")
print(f"Explanation: {result.explanation}")
```

## Related

- [How-to: RAG](./rag.md)
- [Tutorial: RAG](../tutorials/03-rag.md)
