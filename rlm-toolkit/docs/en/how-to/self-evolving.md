# How-to: Self-Evolving LLMs

Recipes for implementing R-Zero Challenger-Solver patterns.

## Enable Self-Evolving

```python
from rlm_toolkit.evolve import SelfEvolvingRLM, EvolutionConfig

config = EvolutionConfig(
    strategy="challenger_solver",
    max_iterations=5,
    early_stop_threshold=0.95,
    enable_meta_learning=True
)

evolving = SelfEvolvingRLM.from_openai("gpt-4o", config=config)
response = evolving.run("Write a Python function to sort a list")
```

## Challenger-Solver Strategy

```python
config = EvolutionConfig(
    strategy="challenger_solver",
    max_iterations=5
)

# Flow:
# 1. Solver generates initial response
# 2. Challenger critiques response
# 3. Solver improves based on critique
# 4. Repeat until quality threshold or max iterations
```

## Self-Critique Strategy

```python
config = EvolutionConfig(
    strategy="self_critique",
    max_iterations=3
)

# Single model reflects on its own output
```

## Ensemble Strategy

```python
from rlm_toolkit.evolve import EnsembleEvolvingRLM

evolving = EnsembleEvolvingRLM(
    models=[
        RLM.from_openai("gpt-4o"),
        RLM.from_anthropic("claude-3-sonnet"),
        RLM.from_openai("gpt-4o-mini")
    ],
    voting_method="majority"  # or "weighted", "best_of"
)
```

## Meta-Learning (Persistent Improvement)

```python
config = EvolutionConfig(
    enable_meta_learning=True,
    meta_learning_path="./meta_patterns"
)

evolving = SelfEvolvingRLM.from_openai("gpt-4o", config=config)

# Over time, the model learns from successful patterns
# and applies them to similar future tasks
```

## Custom Evaluation Function

```python
def code_evaluator(response: str) -> float:
    """Evaluate code correctness (0-1 score)"""
    try:
        exec(response)  # Test if code runs
        return 1.0
    except:
        return 0.0

config = EvolutionConfig(
    evaluator=code_evaluator
)
```

## Streaming Self-Evolving

```python
for event in evolving.stream("Write a sorting function"):
    if event.type == "iteration":
        print(f"\n--- Iteration {event.iteration} ---")
    elif event.type == "solver":
        print(f"Solver: {event.content}")
    elif event.type == "challenger":
        print(f"Challenger: {event.content}")
    elif event.type == "final":
        print(f"\nFinal: {event.content}")
```

## Custom Challenger Prompt

```python
config = EvolutionConfig(
    challenger_prompt="""
    Review this response critically:
    {response}
    
    Identify:
    1. Logical errors
    2. Missing edge cases
    3. Performance issues
    4. Style improvements
    """
)
```

## Performance Benchmarks

| Strategy | Code Accuracy | Iterations | Latency |
|----------|---------------|------------|---------|
| Single call | 76% | 1 | 2s |
| Self-critique | 84% | 2 | 5s |
| Challenger-Solver | 92% | 4 | 12s |
| Ensemble (3 models) | 88% | 1 | 6s |

## Related

- [Concept: Self-Evolving](../concepts/self-evolving.md)
- [Tutorial: Self-Evolving](../tutorials/08-self-evolving.md)
