# Туториал 8: Self-Evolving LLMs

Создавайте AI-системы, которые улучшают себя через использование с помощью динамики R-Zero Challenger-Solver.

## Что такое Self-Evolving?

Self-Evolving LLMs используют новый подход, вдохновлённый DeepSeek-R1:

- **Паттерн R-Zero**: LLM развивает рассуждение без человеческого надзора
- **Challenger-Solver**: Две AI-персоны, которые бросают вызов и улучшают друг друга
- **Непрерывное улучшение**: Становится лучше с каждым взаимодействием
- **Без дорогого fine-tuning**: Чисто inference-time обучение

## Как работает Self-Evolving

```
┌─────────────────────────────────────────────────────────────────┐
│                Архитектура Self-Evolving                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Запрос пользователя                                            │
│       ↓                                                          │
│  SOLVER: Генерирует начальный ответ                             │
│       ↓                                                          │
│  CHALLENGER: Критикует ответ, находит недостатки                │
│       ↓                                                          │
│  SOLVER: Улучшает на основе критики                             │
│       ↓ (повторять пока не удовлетворено или max итераций)      │
│                                                                  │
│  МЕТА-ОБУЧЕНИЕ: Записывает успешные паттерны                    │
│       ↓                                                          │
│  Будущие запросы получают пользу от изученных паттернов         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Предварительные требования

```bash
pip install rlm-toolkit[all]
export OPENAI_API_KEY=your-key
```

## Шаг 1: Базовый Self-Evolving RLM

```python
from rlm_toolkit import RLM, RLMConfig
from rlm_toolkit.evolve import SelfEvolvingRLM

# Создаём self-evolving экземпляр
evolving = SelfEvolvingRLM.from_openai(
    "gpt-4o",
    strategy="challenger_solver",
    max_iterations=3
)

# Первая попытка - учится из процесса
result = evolving.run("Объясни квантовую запутанность простыми словами")
print(result.answer)

# Смотрим эволюцию
print(f"Итерации: {result.iterations}")
print(f"Улучшения: {result.improvements}")
```

## Шаг 2: Настройка стратегий эволюции

```python
from rlm_toolkit.evolve import SelfEvolvingRLM, EvolutionConfig

config = EvolutionConfig(
    # Стратегия
    strategy="challenger_solver",  # или "self_critique", "ensemble"
    
    # Итерации
    max_iterations=5,
    early_stop_threshold=0.95,  # Остановка когда качество > 0.95
    
    # Настройки Challenger
    challenger_temperature=0.7,  # Более креативные вызовы
    critic_depth="thorough",     # shallow, medium, thorough
    
    # Мета-обучение
    enable_meta_learning=True,
    meta_store_path="./evolution_cache",
)

evolving = SelfEvolvingRLM.from_openai("gpt-4o", config=config)
```

## Шаг 3: Наблюдение за процессом эволюции

```python
from rlm_toolkit.evolve import SelfEvolvingRLM

evolving = SelfEvolvingRLM.from_openai("gpt-4o", verbose=True)

result = evolving.run("Напиши алгоритм сортировки на Python")

# Детальная трассировка эволюции
for iteration in result.evolution_trace:
    print(f"\n--- Итерация {iteration.round} ---")
    print(f"Ответ Solver: {iteration.solver_response[:200]}...")
    print(f"Критика Challenger: {iteration.challenger_critique}")
    print(f"Оценка качества: {iteration.quality_score}")
```

Пример вывода:
```
--- Итерация 1 ---
Ответ Solver: def bubble_sort(arr): for i in range...
Критика Challenger: Реализация работает, но O(n²). 
  Рассмотри более эффективные алгоритмы, например quicksort.
Оценка качества: 0.65

--- Итерация 2 ---
Ответ Solver: def quicksort(arr): if len(arr) <= 1...
Критика Challenger: Хорошее улучшение! Но нет обработки 
  краевых случаев, например пустых массивов.
Оценка качества: 0.85

--- Итерация 3 ---
Ответ Solver: def quicksort(arr): """Эффективная сортировка...
Критика Challenger: Отлично! Обрабатывает краевые случаи, 
  есть docstring, хороший стиль.
Оценка качества: 0.95
```

## Шаг 4: Разные стратегии эволюции

### Challenger-Solver (по умолчанию)
```python
# Две персоны: одна генерирует, другая критикует
config = EvolutionConfig(strategy="challenger_solver")
```

### Self-Critique
```python
# Одна модель критикует саму себя
config = EvolutionConfig(
    strategy="self_critique",
    critique_prompt="Проанализируй недостатки своего ответа и улучши"
)
```

### Ensemble
```python
# Несколько моделей голосуют за лучший подход
config = EvolutionConfig(
    strategy="ensemble",
    ensemble_size=3,
    voting_method="consensus"
)
```

## Шаг 5: Мета-обучение

Сохраняем и переиспользуем успешные паттерны:

```python
from rlm_toolkit.evolve import SelfEvolvingRLM, MetaStore

# Создаём персистентное мета-хранилище
meta_store = MetaStore(path="./meta_learning")

evolving = SelfEvolvingRLM.from_openai(
    "gpt-4o",
    meta_store=meta_store
)

# Первый запрос - полная эволюция
evolving.run("Напиши функцию бинарного поиска")

# Похожие будущие запросы используют изученные паттерны
evolving.run("Напиши функцию линейного поиска")  # Быстрее!

# Просмотр изученных паттернов
patterns = meta_store.get_patterns(topic="algorithms")
print(patterns)
```

## Шаг 6: Доменно-специфичная эволюция

Обучение для конкретных доменов:

```python
from rlm_toolkit.evolve import SelfEvolvingRLM, DomainConfig

# Анализ юридических документов
legal_config = DomainConfig(
    domain="legal",
    critique_focus=[
        "юридическая точность",
        "корректность ссылок",
        "применимость юрисдикции"
    ],
    quality_metrics=[
        "релевантность прецедентов",
        "структура аргументации"
    ]
)

# Медицинский анализ
medical_config = DomainConfig(
    domain="medical",
    critique_focus=[
        "клиническая точность",
        "доказательная база",
        "осведомлённость о противопоказаниях"
    ],
    safety_checks=True
)

legal_evolving = SelfEvolvingRLM.from_openai("gpt-4o", domain_config=legal_config)
```

## Шаг 7: Комбинация с другими функциями

### С памятью
```python
from rlm_toolkit.evolve import SelfEvolvingRLM
from rlm_toolkit.memory import HierarchicalMemory

memory = HierarchicalMemory()

evolving = SelfEvolvingRLM.from_openai(
    "gpt-4o",
    memory=memory  # Эволюция осведомлена о контексте
)
```

### С инструментами
```python
from rlm_toolkit.evolve import SelfEvolvingRLM
from rlm_toolkit.tools import Calculator, WebSearch

evolving = SelfEvolvingRLM.from_openai(
    "gpt-4o",
    tools=[Calculator(), WebSearch()],
    evolve_tool_usage=True  # Улучшать выбор инструментов
)
```

## Полное приложение: Эволюционирующий код-ассистент

```python
# evolving_code_assistant.py
from rlm_toolkit.evolve import SelfEvolvingRLM, EvolutionConfig, MetaStore
from rlm_toolkit.tools import SecurePythonREPL
from rlm_toolkit.memory import HierarchicalMemory

class EvolvingCodeAssistant:
    def __init__(self):
        # Персистентное обучение
        self.meta_store = MetaStore(path="./code_evolution")
        self.memory = HierarchicalMemory(persist_directory="./code_memory")
        
        # Конфигурация эволюции для кода
        config = EvolutionConfig(
            strategy="challenger_solver",
            max_iterations=4,
            critique_focus=[
                "корректность кода",
                "эффективность",
                "читаемость",
                "обработка краевых случаев"
            ],
            enable_meta_learning=True
        )
        
        self.rlm = SelfEvolvingRLM.from_openai(
            "gpt-4o",
            config=config,
            meta_store=self.meta_store,
            memory=self.memory,
            tools=[SecurePythonREPL(sandbox=True)]
        )
    
    def generate_code(self, task: str) -> dict:
        """Генерация и эволюция кода для задачи."""
        result = self.rlm.run(f"Напиши Python-код для: {task}")
        
        return {
            "code": result.answer,
            "iterations": result.iterations,
            "improvements": result.improvements,
            "quality_score": result.final_quality_score
        }
    
    def explain_evolution(self, result) -> str:
        """Объяснение эволюции кода."""
        explanation = []
        for i, trace in enumerate(result.evolution_trace, 1):
            explanation.append(
                f"Раунд {i}: {trace.challenger_critique}\n"
                f"Улучшение: {trace.improvement_made}"
            )
        return "\n\n".join(explanation)

def main():
    print("🧬 Эволюционирующий код-ассистент")
    print("   Наблюдайте, как код улучшается в реальном времени!\n")
    
    assistant = EvolvingCodeAssistant()
    
    while True:
        task = input("📝 Задача: ").strip()
        
        if task.lower() in ['выход', 'quit', 'exit']:
            break
        
        print("\n⏳ Эволюция решения...\n")
        result = assistant.generate_code(task)
        
        print(f"✅ Финальный код (Качество: {result['quality_score']:.0%}):\n")
        print(result['code'])
        print(f"\n📈 Эволюция через {result['iterations']} итераций")
        print(f"🔧 Сделано улучшений: {result['improvements']}\n")

if __name__ == "__main__":
    main()
```

## Бенчмарки

| Задача | Base GPT-4 | + Self-Evolving | Улучшение |
|--------|-----------|-----------------|-----------|
| Корректность кода | 78% | 94% | +16% |
| Математические рассуждения | 82% | 95% | +13% |
| Сложные запросы | 71% | 89% | +18% |

## Лучшие практики

!!! tip "Количество итераций"
    3-5 итераций оптимально. Больше итераций имеют убывающую отдачу.

!!! tip "Ранняя остановка"
    Используйте порог качества для ранней остановки:
    ```python
    config = EvolutionConfig(early_stop_threshold=0.9)
    ```

!!! tip "Мета-обучение"
    Всегда включайте мета-обучение для повторного использования:
    ```python
    meta_store = MetaStore(path="./cache")
    ```

!!! warning "Стоимость"
    Self-evolving использует 2-5x больше токенов. Используйте для ценных задач.

## Следующие шаги

- [Туториал 9: Multi-Agent](09-multiagent.md)
- [Концепция: Self-Evolving](../concepts/self-evolving.md)
- [Концепция: Паттерн R-Zero](../concepts/r-zero.md)
