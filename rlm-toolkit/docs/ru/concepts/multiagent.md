# Многоагентные системы

RLM-Toolkit реализует децентрализованные P2P многоагентные системы с архитектурой Meta Matrix.

## Что такое Multi-Agent?

Многоагентные системы (MAS) обеспечивают:
- **Коллаборация**: Агенты работают вместе над сложными задачами
- **Специализация**: Каждый агент обрабатывает конкретные домены
- **Масштабируемость**: Добавление агентов без перепроектирования системы
- **Отказоустойчивость**: Нет единой точки отказа

## Топологии агентов

### Централизованная (Оркестратор)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Централизованная топология                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                    ┌─────────────┐                              │
│                    │ Оркестратор │                              │
│                    └──────┬──────┘                              │
│              ┌────────────┼────────────┐                        │
│              ▼            ▼            ▼                        │
│        ┌─────────┐  ┌─────────┐  ┌─────────┐                   │
│        │ Агент A │  │ Агент B │  │ Агент C │                   │
│        └─────────┘  └─────────┘  └─────────┘                   │
│                                                                  │
│        ✅ Простое управление                                    │
│        ❌ Единая точка отказа                                   │
│        ❌ Ограниченная масштабируемость                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Децентрализованная (P2P)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Децентрализованная (P2P) топология           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│             ┌─────────┐ ←──→ ┌─────────┐                       │
│             │ Агент A │      │ Агент B │                       │
│             └────┬────┘      └────┬────┘                       │
│                  │                │                              │
│                  ▼                ▼                              │
│             ┌─────────┐ ←──→ ┌─────────┐                       │
│             │ Агент C │      │ Агент D │                       │
│             └─────────┘      └─────────┘                       │
│                                                                  │
│        ✅ Нет единой точки отказа                               │
│        ✅ Высокая масштабируемость                              │
│        ✅ Отказоустойчивость                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Архитектура Meta Matrix

Децентрализованная многоагентная система RLM:

```python
from rlm_toolkit.agents.multiagent import MetaMatrix, Agent, TrustZone

# Создание сети Meta Matrix
matrix = MetaMatrix(
    topology="mesh",
    consensus="raft",
    enable_discovery=True
)

# Определение специализированных агентов
researcher = Agent(
    name="researcher",
    description="Ищет и анализирует информацию",
    llm=RLM.from_openai("gpt-4o"),
    tools=[WebSearchTool(), ArxivTool()]
)

analyst = Agent(
    name="analyst",
    description="Анализирует данные и создаёт отчёты",
    llm=RLM.from_openai("gpt-4o"),
    tools=[PythonREPL(), ChartTool()]
)

writer = Agent(
    name="writer",
    description="Пишет понятный, увлекательный контент",
    llm=RLM.from_anthropic("claude-3-sonnet"),
    tools=[FileWriter()]
)

# Регистрация агентов
matrix.register(researcher)
matrix.register(analyst)
matrix.register(writer)

# Запуск совместной задачи
result = matrix.run(
    "Исследуй AI тренды 2024, проанализируй данные, напиши отчёт"
)
```

## Зоны доверия

Границы безопасности для коммуникации агентов:

```python
from rlm_toolkit.agents.multiagent import TrustZone

# Определение зон доверия
public_zone = TrustZone(
    name="public",
    level=0,
    allowed_agents=["assistant"]
)

internal_zone = TrustZone(
    name="internal",
    level=1,
    allowed_agents=["researcher", "analyst"]
)

confidential_zone = TrustZone(
    name="confidential",
    level=2,
    allowed_agents=["data_processor"],
    encryption_enabled=True
)

# Назначение зон агентам
researcher = Agent(
    name="researcher",
    trust_zone=internal_zone,
    ...
)

data_processor = Agent(
    name="data_processor",
    trust_zone=confidential_zone,
    encryption_key="your-256-bit-key"
)
```

## Паттерны коммуникации

### Прямые сообщения

```python
# Агент A отправляет Агенту B
researcher.send_message(
    to="analyst",
    content="Вот данные исследования",
    data=research_results
)

# Агент B получает
message = analyst.receive_message()
```

### Broadcast

```python
# Рассылка всем агентам
matrix.broadcast(
    from_agent="orchestrator",
    content="Доступна новая задача",
    data=task_details
)
```

### Запрос-Ответ

```python
# Синхронный запрос с ответом
response = researcher.request(
    to="analyst",
    action="analyze",
    data=raw_data,
    timeout=30
)
```

## Специализация агентов

```python
# Агент-исследователь
researcher = Agent(
    name="researcher",
    system_prompt="""Ты специалист по исследованиям.
    Твоя роль - находить и верифицировать информацию.
    Всегда указывай источники.""",
    tools=[WebSearchTool(), WikipediaTool(), ArxivTool()]
)

# Агент-программист
coder = Agent(
    name="coder",
    system_prompt="""Ты эксперт по Python.
    Пиши чистый, эффективный, документированный код.
    Всегда включай тесты.""",
    tools=[PythonREPL(), FileWriter(), GitTool()]
)

# Агент-ревьюер
reviewer = Agent(
    name="reviewer",
    system_prompt="""Ты code reviewer.
    Проверяй баги, проблемы безопасности и лучшие практики.
    Будь тщательным, но конструктивным.""",
    tools=[CodeAnalyzer(), SecurityScanner()]
)
```

## Паттерны Workflow

### Последовательный

```python
# Агенты работают последовательно
workflow = SequentialWorkflow([
    ("researcher", "Найти информацию по теме X"),
    ("analyst", "Проанализировать находки"),
    ("writer", "Написать резюме")
])

result = matrix.run_workflow(workflow)
```

### Параллельный

```python
# Агенты работают одновременно
workflow = ParallelWorkflow({
    "researcher": "Исследовать аспект A",
    "analyst": "Анализировать существующие данные B",
    "coder": "Прототипировать решение C"
})

results = matrix.run_workflow(workflow)
# results = {"researcher": ..., "analyst": ..., "coder": ...}
```

### Иерархический

```python
# Менеджер делегирует специализированным командам
workflow = HierarchicalWorkflow(
    manager="project_lead",
    teams={
        "research_team": ["researcher_1", "researcher_2"],
        "dev_team": ["coder_1", "coder_2", "tester"]
    }
)

result = matrix.run_workflow(workflow, task="Построить фичу X")
```

## Механизмы консенсуса

```python
# Голосование по решениям
matrix = MetaMatrix(
    consensus="voting",
    voting_threshold=0.6  # Требуется 60% согласие
)

# Консенсус Raft (выбор лидера)
matrix = MetaMatrix(
    consensus="raft",
    election_timeout=5
)

# Byzantine fault tolerance
matrix = MetaMatrix(
    consensus="pbft",
    fault_tolerance=1  # Терпеть 1 неисправного агента
)
```

## Мониторинг и наблюдаемость

```python
from rlm_toolkit.callbacks import MultiAgentCallback

# Мониторинг взаимодействий агентов
callback = MultiAgentCallback(
    log_messages=True,
    log_tool_calls=True,
    metrics_endpoint="http://localhost:8080"
)

matrix = MetaMatrix(callbacks=[callback])

# Доступ к метрикам
metrics = matrix.get_metrics()
print(metrics)
# {
#   "total_messages": 45,
#   "agent_activity": {"researcher": 20, "analyst": 15, ...},
#   "avg_response_time": 1.5,
#   "consensus_rounds": 3
# }
```

## Лучшие практики

!!! tip "Дизайн агентов"
    - Сохраняйте фокус агентов на конкретных доменах
    - Чёткое разделение ответственности
    - Определяйте явные протоколы коммуникации

!!! tip "Безопасность"
    - Используйте зоны доверия для чувствительных данных
    - Включайте шифрование для конфиденциальных зон
    - Аудитируйте всю межзональную коммуникацию

!!! tip "Масштабируемость"
    - Начинайте с минимального количества агентов
    - Добавляйте агентов по мере необходимости
    - Используйте P2P топологию для больших систем

!!! tip "Отладка"
    - Включите подробное логирование
    - Мониторьте потоки сообщений
    - Используйте callbacks для наблюдаемости

## Связанное

- [Туториал: Multi-Agent](../tutorials/09-multiagent.md)
- [Концепция: Агенты](./agents.md)
- [Концепция: Безопасность](./security.md)
