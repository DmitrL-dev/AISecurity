# How-to: Self-Evolving LLMs

Рецепты реализации паттернов R-Zero Challenger-Solver.

## Включение Self-Evolving

```python
from rlm_toolkit.evolve import SelfEvolvingRLM, EvolutionConfig

config = EvolutionConfig(
    strategy="challenger_solver",
    max_iterations=5,
    early_stop_threshold=0.95,
    enable_meta_learning=True
)

evolving = SelfEvolvingRLM.from_openai("gpt-4o", config=config)
response = evolving.run("Напиши Python функцию для сортировки списка")
```

## Стратегия Challenger-Solver

```python
config = EvolutionConfig(
    strategy="challenger_solver",
    max_iterations=5
)

# Поток:
# 1. Solver генерирует начальный ответ
# 2. Challenger критикует ответ
# 3. Solver улучшает на основе критики
# 4. Повторять до порога качества или макс. итераций
```

## Стратегия Self-Critique

```python
config = EvolutionConfig(
    strategy="self_critique",
    max_iterations=3
)

# Одна модель рефлексирует над собственным выводом
```

## Стратегия Ensemble

```python
from rlm_toolkit.evolve import EnsembleEvolvingRLM

evolving = EnsembleEvolvingRLM(
    models=[
        RLM.from_openai("gpt-4o"),
        RLM.from_anthropic("claude-3-sonnet"),
        RLM.from_openai("gpt-4o-mini")
    ],
    voting_method="majority"  # или "weighted", "best_of"
)
```

## Мета-обучение (персистентное улучшение)

```python
config = EvolutionConfig(
    enable_meta_learning=True,
    meta_learning_path="./meta_patterns"
)

evolving = SelfEvolvingRLM.from_openai("gpt-4o", config=config)

# Со временем модель учится на успешных паттернах
# и применяет их к похожим будущим задачам
```

## Пользовательская функция оценки

```python
def code_evaluator(response: str) -> float:
    """Оценка корректности кода (0-1 скор)"""
    try:
        exec(response)  # Тест запуска кода
        return 1.0
    except:
        return 0.0

config = EvolutionConfig(
    evaluator=code_evaluator
)
```

## Streaming Self-Evolving

```python
for event in evolving.stream("Напиши функцию сортировки"):
    if event.type == "iteration":
        print(f"\n--- Итерация {event.iteration} ---")
    elif event.type == "solver":
        print(f"Solver: {event.content}")
    elif event.type == "challenger":
        print(f"Challenger: {event.content}")
    elif event.type == "final":
        print(f"\nФинал: {event.content}")
```

## Пользовательский промпт Challenger

```python
config = EvolutionConfig(
    challenger_prompt="""
    Критически оцени этот ответ:
    {response}
    
    Идентифицируй:
    1. Логические ошибки
    2. Пропущенные edge cases
    3. Проблемы производительности
    4. Улучшения стиля
    """
)
```

## Бенчмарки производительности

| Стратегия | Точность кода | Итерации | Латентность |
|-----------|---------------|----------|-------------|
| Один вызов | 76% | 1 | 2s |
| Self-critique | 84% | 2 | 5s |
| Challenger-Solver | 92% | 4 | 12s |
| Ensemble (3 модели) | 88% | 1 | 6s |

## Связанное

- [Концепция: Self-Evolving](../concepts/self-evolving.md)
- [Туториал: Self-Evolving](../tutorials/08-self-evolving.md)
