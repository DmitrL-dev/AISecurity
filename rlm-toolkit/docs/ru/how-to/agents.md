# How-to: Использование агентов

Рецепты создания и настройки агентов.

## Создание простого агента

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import Tool

@Tool(name="calculator")
def calc(expression: str) -> str:
    return str(eval(expression))

agent = ReActAgent.from_openai("gpt-4o", tools=[calc])
result = agent.run("Что такое 25 * 4?")
```

## Добавление нескольких инструментов

```python
from rlm_toolkit.tools import PythonREPL, WebSearchTool, FileReader

agent = ReActAgent.from_openai(
    "gpt-4o",
    tools=[
        PythonREPL(max_execution_time=30),
        WebSearchTool(provider="ddg"),
        FileReader()
    ]
)
```

## Настройка лимитов агента

```python
from rlm_toolkit.agents import AgentConfig

config = AgentConfig(
    max_iterations=10,
    max_execution_time=300,
    verbose=True
)

agent = ReActAgent.from_openai("gpt-4o", config=config, tools=[...])
```

## Использование Plan-Execute агента

```python
from rlm_toolkit.agents import PlanExecuteAgent

agent = PlanExecuteAgent.from_openai(
    "gpt-4o",
    tools=[...],
    max_iterations=10
)

result = agent.run("Исследуй Python фреймворки и сравни их")
```

## Агент с памятью

```python
from rlm_toolkit.memory import HierarchicalMemory

memory = HierarchicalMemory(persist_directory="./memory")
agent = ReActAgent.from_openai("gpt-4o", memory=memory, tools=[...])
```

## Streaming вывода агента

```python
for event in agent.stream("Проанализируй данные"):
    if event.type == "thought":
        print(f"Думает: {event.content}")
    elif event.type == "action":
        print(f"Инструмент: {event.tool_name}")
    elif event.type == "final":
        print(f"Ответ: {event.content}")
```

## Безопасный агент

```python
from rlm_toolkit.agents import SecureAgent
from rlm_toolkit.tools import SecurePythonREPL

secure_repl = SecurePythonREPL(
    allowed_imports=["math", "json"],
    max_execution_time=5,
    enable_network=False
)

agent = SecureAgent(
    name="secure",
    tools=[secure_repl]
)
```

## Пользовательский инструмент

```python
from rlm_toolkit.tools import Tool
from typing import Annotated

@Tool(name="weather", description="Получить погоду для города")
def get_weather(
    city: Annotated[str, "Название города"]
) -> str:
    return f"Погода в {city}: 22°C"
```

## Связанное

- [Концепция: Агенты](../concepts/agents.md)
- [Туториал: Агенты](../tutorials/04-agents.md)
