# How-to: Многоагентные системы

Рецепты построения многоагентных приложений.

## Создание сети Meta Matrix

```python
from rlm_toolkit.agents.multiagent import MetaMatrix, Agent

matrix = MetaMatrix(
    topology="mesh",
    consensus="raft",
    enable_discovery=True
)
```

## Определение специализированных агентов

```python
from rlm_toolkit import RLM
from rlm_toolkit.agents.multiagent import Agent
from rlm_toolkit.tools import WebSearchTool, PythonREPL

researcher = Agent(
    name="researcher",
    description="Ищет и анализирует информацию",
    llm=RLM.from_openai("gpt-4o"),
    tools=[WebSearchTool()]
)

coder = Agent(
    name="coder",
    description="Пишет и выполняет Python код",
    llm=RLM.from_openai("gpt-4o"),
    tools=[PythonREPL()]
)

writer = Agent(
    name="writer",
    description="Пишет понятную документацию",
    llm=RLM.from_anthropic("claude-3-sonnet"),
    tools=[]
)
```

## Регистрация и запуск

```python
matrix.register(researcher)
matrix.register(coder)
matrix.register(writer)

result = matrix.run(
    "Исследуй тренды Python, проанализируй кодом, напиши отчёт"
)
```

## Последовательный workflow

```python
from rlm_toolkit.agents.multiagent import SequentialWorkflow

workflow = SequentialWorkflow([
    ("researcher", "Найти бенчмарки Python фреймворков"),
    ("coder", "Создать сравнительный график"),
    ("writer", "Написать итоговый отчёт")
])

result = matrix.run_workflow(workflow)
```

## Параллельный workflow

```python
from rlm_toolkit.agents.multiagent import ParallelWorkflow

workflow = ParallelWorkflow({
    "researcher": "Исследовать аспект A",
    "coder": "Построить прототип B"
})

results = matrix.run_workflow(workflow)
```

## Коммуникация агентов

```python
# Прямое сообщение
researcher.send_message(
    to="coder",
    content="Вот данные",
    data=research_results
)

# Рассылка
matrix.broadcast(
    from_agent="leader",
    content="Доступна новая задача"
)

# Запрос-ответ
response = researcher.request(
    to="coder",
    action="analyze",
    data=raw_data,
    timeout=30
)
```

## Зоны доверия

```python
from rlm_toolkit.agents.multiagent import TrustZone

confidential = TrustZone(
    name="confidential",
    level=2,
    encryption_enabled=True
)

secure_agent = Agent(
    name="data_processor",
    trust_zone=confidential,
    encryption_key="your-256-bit-key"
)
```

## Мониторинг

```python
from rlm_toolkit.callbacks import MultiAgentCallback

callback = MultiAgentCallback(log_messages=True)
matrix = MetaMatrix(callbacks=[callback])

# Получение метрик
metrics = matrix.get_metrics()
print(f"Сообщений: {metrics['total_messages']}")
print(f"Активность: {metrics['agent_activity']}")
```

## Связанное

- [Концепция: Multi-Agent](../concepts/multiagent.md)
- [Туториал: Multi-Agent](../tutorials/09-multiagent.md)
