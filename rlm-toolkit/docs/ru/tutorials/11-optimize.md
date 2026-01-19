# Туториал 11: Оптимизация промптов с DSPy

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> Научитесь автоматически оптимизировать промпты для лучшей точности

## Что вы изучите

- Создание DSPy сигнатур
- Использование ChainOfThought для рассуждений
- Оптимизация с BootstrapFewShot
- Измерение улучшений

## Требования

```bash
pip install rlm-toolkit
```

## Часть 1: Постановка задачи

Построим классификатор тикетов поддержки, который улучшается сам.

### 1.1 Определяем задачу

```python
from rlm_toolkit.optimize import Signature, Example

# Определяем что хотим
sig = Signature(
    inputs=["ticket"],
    outputs=["category", "priority"],
    instructions="Классифицируй тикет поддержки"
)

# Создаём обучающие примеры
trainset = [
    Example(
        ticket="Мой заказ не пришёл за 2 недели",
        category="доставка",
        priority="высокий"
    ),
    Example(
        ticket="Как сменить пароль?",
        category="аккаунт",
        priority="низкий"
    ),
    Example(
        ticket="Приложение падает при открытии настроек",
        category="баг",
        priority="высокий"
    ),
    Example(
        ticket="Какие у вас часы работы?",
        category="общее",
        priority="низкий"
    ),
    # Добавьте 20+ примеров для лучших результатов
]
```

---

## Часть 2: Базовая модель

### 2.1 Простой предиктор

```python
from rlm_toolkit.optimize import Predict
from rlm_toolkit.providers import OpenAIProvider

provider = OpenAIProvider("gpt-4o")
baseline = Predict(sig, provider)

# Тестируем
result = baseline(ticket="Не могу войти в аккаунт")
print(f"Категория: {result['category']}")
print(f"Приоритет: {result['priority']}")
```

### 2.2 Измеряем базовую линию

```python
def evaluate(model, testset):
    correct = 0
    for example in testset:
        pred = model(ticket=example.ticket)
        if pred["category"] == example.category:
            correct += 1
    return correct / len(testset)

baseline_accuracy = evaluate(baseline, testset)
print(f"Базовая: {baseline_accuracy:.1%}")  # ~65%
```

---

## Часть 3: Добавляем рассуждение

### 3.1 ChainOfThought

```python
from rlm_toolkit.optimize import ChainOfThought

cot = ChainOfThought(sig, provider)

result = cot(ticket="С меня списали оплату дважды")
print(f"Рассуждение: {result['reasoning']}")
print(f"Категория: {result['category']}")
print(f"Приоритет: {result['priority']}")
```

### 3.2 Измеряем улучшение

```python
cot_accuracy = evaluate(cot, testset)
print(f"ChainOfThought: {cot_accuracy:.1%}")  # ~75%
```

---

## Часть 4: Автоматическая оптимизация

### 4.1 BootstrapFewShot

```python
from rlm_toolkit.optimize import BootstrapFewShot

def category_match(pred, gold):
    return pred["category"] == gold.category

optimizer = BootstrapFewShot(
    metric=category_match,
    num_candidates=10
)

optimized = optimizer.compile(
    ChainOfThought(sig, provider),
    trainset=trainset
)
```

### 4.2 Финальная оценка

```python
optimized_accuracy = evaluate(optimized, testset)
print(f"Оптимизированная: {optimized_accuracy:.1%}")  # ~92%

print(f"""
Сводка улучшений
----------------
Базовая:        {baseline_accuracy:.1%}
ChainOfThought: {cot_accuracy:.1%}
Оптимизированная: {optimized_accuracy:.1%}

Прирост: +{(optimized_accuracy - baseline_accuracy) * 100:.0f}%
""")
```

---

## Часть 5: Production деплой

### 5.1 Сохранение оптимизированной модели

```python
import pickle

with open("classifier_v1.pkl", "wb") as f:
    pickle.dump(optimized, f)
```

### 5.2 Загрузка и использование

```python
with open("classifier_v1.pkl", "rb") as f:
    classifier = pickle.load(f)

# Production использование
result = classifier(ticket="Где мой возврат?")
print(f"→ {result['category']} ({result['priority']})")
```

---

## Результаты

| Модель | Точность | Латентность |
|--------|----------|-------------|
| Базовая | 65% | 0.5s |
| ChainOfThought | 75% | 1.2s |
| **Оптимизированная** | **92%** | 1.0s |

---

## Следующие шаги

- [Концепция: Оптимизация промптов](../concepts/optimize.md)
- [Туториал: Observability](12-observability.md)
- [Туториал: Self-Evolving](08-self-evolving.md)
