# Оптимизация промптов (DSPy)

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **Автоматическая оптимизация промптов** — Определяй что, а не как

## Обзор

RLM-Toolkit включает DSPy-style оптимизацию:
- **Signatures** — Декларативные спецификации вход/выход
- **Modules** — Predict, ChainOfThought, SelfRefine
- **Optimizers** — BootstrapFewShot, PromptOptimizer

## Быстрый старт

```python
from rlm_toolkit.optimize import Signature, Predict
from rlm_toolkit.providers import OpenAIProvider

# Определяем сигнатуру
sig = Signature(
    inputs=["question", "context"],
    outputs=["answer"],
    instructions="Ответь на вопрос на основе контекста"
)

# Создаём предиктор
provider = OpenAIProvider("gpt-4o")
predictor = Predict(sig, provider)

# Используем
result = predictor(
    question="Какая столица?",
    context="Франция — страна в Европе. Париж — её столица."
)
print(result["answer"])  # "Париж"
```

## Сигнатуры

### Базовая сигнатура

```python
from rlm_toolkit.optimize import Signature

# Q&A сигнатура
qa_sig = Signature(
    inputs=["question"],
    outputs=["answer"],
    instructions="Ответь на вопрос точно"
)

# Сигнатура классификации
classify_sig = Signature(
    inputs=["text"],
    outputs=["category", "confidence"],
    instructions="Классифицируй текст: tech, sports, politics"
)
```

### Фабричные функции

```python
from rlm_toolkit.optimize import (
    create_qa_signature,
    create_summarize_signature,
    create_classify_signature
)

# Готовые сигнатуры
qa = create_qa_signature()
summarize = create_summarize_signature(max_words=100)
classify = create_classify_signature(categories=["positive", "negative", "neutral"])
```

## Модули

### Predict

Простое одношаговое предсказание:

```python
from rlm_toolkit.optimize import Predict

predictor = Predict(signature, provider)
result = predictor(question="Сколько будет 2+2?")
```

### ChainOfThought

Пошаговое рассуждение:

```python
from rlm_toolkit.optimize import ChainOfThought

cot = ChainOfThought(signature, provider)
result = cot(question="Сколько будет 15% от 80?")

print(result["reasoning"])  # Пошаговое объяснение
print(result["answer"])     # "12"
```

### SelfRefine

Итеративное самоулучшение:

```python
from rlm_toolkit.optimize import SelfRefine

refiner = SelfRefine(
    signature, 
    provider,
    max_iterations=3,
    stop_condition=lambda r: r["confidence"] > 0.9
)

result = refiner(question="Сложная задача на рассуждение...")
print(f"Итераций: {result['iterations']}")
print(f"Финальный ответ: {result['answer']}")
```

## Оптимизаторы

### BootstrapFewShot

Автоматический выбор лучших few-shot примеров:

```python
from rlm_toolkit.optimize import Predict, BootstrapFewShot, Example

# Обучающие примеры
trainset = [
    Example(question="Столица Франции?", answer="Париж"),
    Example(question="Столица Японии?", answer="Токио"),
    Example(question="Столица Бразилии?", answer="Бразилиа"),
    # ... больше примеров
]

# Функция метрики
def exact_match(prediction, ground_truth):
    return prediction["answer"].lower() == ground_truth["answer"].lower()

# Оптимизация
optimizer = BootstrapFewShot(metric=exact_match, num_candidates=10)
optimized_predictor = optimizer.compile(
    Predict(signature, provider),
    trainset=trainset
)

# Теперь автоматически использует лучшие примеры
result = optimized_predictor(question="Столица Германии?")
```

### PromptOptimizer

Оптимизация инструкций промпта:

```python
from rlm_toolkit.optimize import PromptOptimizer

optimizer = PromptOptimizer(
    metric=exact_match,
    num_trials=20,
    temperature=0.7
)

# Находим лучшие инструкции
optimized = optimizer.optimize(
    module=Predict(signature, provider),
    trainset=trainset,
    valset=valset
)

print(f"Лучшие инструкции: {optimized.signature.instructions}")
print(f"Точность на валидации: {optimized.val_score:.2%}")
```

## Практические примеры

### Пример 1: Классификатор тикетов поддержки

```python
from rlm_toolkit.optimize import Signature, ChainOfThought, BootstrapFewShot

# Определяем задачу
sig = Signature(
    inputs=["ticket_text"],
    outputs=["category", "priority", "suggested_action"],
    instructions="Классифицируй тикет и предложи действие"
)

# Обучающие данные
trainset = [
    Example(
        ticket_text="Мой заказ не пришёл",
        category="доставка",
        priority="высокий", 
        suggested_action="Проверить трекинг, предложить возврат если >7 дней"
    ),
    # ... 50+ примеров
]

# Оптимизация
classifier = ChainOfThought(sig, provider)
optimizer = BootstrapFewShot(metric=category_match, num_candidates=5)
optimized = optimizer.compile(classifier, trainset=trainset)

# Production использование
result = optimized(ticket_text="Где моя посылка?")
print(f"Категория: {result['category']}")
print(f"Приоритет: {result['priority']}")
print(f"Действие: {result['suggested_action']}")
```

### Пример 2: Ассистент код-ревью

```python
sig = Signature(
    inputs=["code", "language"],
    outputs=["issues", "suggestions", "security_concerns"],
    instructions="Проверь код на баги, стиль и безопасность"
)

reviewer = SelfRefine(sig, provider, max_iterations=2)

result = reviewer(
    code="""
def login(user, password):
    query = f"SELECT * FROM users WHERE user='{user}'"
    return db.execute(query)
""",
    language="python"
)

print("Проблемы безопасности:", result["security_concerns"])
# ["SQL injection уязвимость в построении запроса"]
```

### Пример 3: Многошаговое исследование

```python
from rlm_toolkit.optimize import ChainOfThought

# Сигнатура исследования с рассуждением
sig = Signature(
    inputs=["topic", "sources"],
    outputs=["summary", "key_findings", "confidence"],
    instructions="Проанализируй источники и извлеки ключевые выводы"
)

researcher = ChainOfThought(sig, provider)

result = researcher(
    topic="Влияние изменения климата на сельское хозяйство",
    sources=[doc1, doc2, doc3]
)

print(f"Уверенность: {result['confidence']}")
print(f"Ключевые выводы: {result['key_findings']}")
```

## Best Practices

| Практика | Польза |
|----------|--------|
| Начни с Predict | Простая базовая линия |
| Добавь CoT для сложных задач | Лучшая точность |
| Используй 20+ примеров | Надёжная оптимизация |
| Валидируй на hold-out | Избегай переобучения |
| Мониторь в production | Детекция дрифта промптов |

## Связанное

- [Self-Evolving LLMs](self-evolving.md)
- [Туториал: Первое приложение](../tutorials/01-first-app.md)
- [Observability](observability.md)
