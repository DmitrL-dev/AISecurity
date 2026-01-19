# Agentic Workflows

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **Высокоуровневые агентные паттерны** для сложных задач

## Обзор

Модуль `agentic` предоставляет workflow'ы:
- **Plan-and-Execute** — Многошаговое планирование
- **ReAct** — Рассуждение + Действие
- **Reflection** — Самокритика и улучшение
- **Multi-turn** — Управление разговором

## Plan-and-Execute

```python
from rlm_toolkit.agentic import PlanAndExecute
from rlm_toolkit.tools import WebSearchTool, PythonREPL

agent = PlanAndExecute(
    model="gpt-4o",
    tools=[WebSearchTool(), PythonREPL()],
    max_steps=10
)

result = agent.run("""
Исследуй топ-5 компаний по капитализации
и создай график сравнения их роста.
""")

print(result.plan)    # Пошаговый план
print(result.output)  # Финальный результат
```

## ReAct

```python
from rlm_toolkit.agentic import ReActAgent

agent = ReActAgent(
    model="gpt-4o",
    tools=[WebSearchTool()],
    max_iterations=5
)

result = agent.run("Какая самая высокая температура была зафиксирована в Долине Смерти?")
# Thought: Нужно найти записи о температуре
# Action: web_search("highest temperature Death Valley")
# Observation: 134°F (56.7°C) 10 июля 1913
# Final Answer: 134°F
```

## Reflection

```python
from rlm_toolkit.agentic import ReflectionAgent

agent = ReflectionAgent(
    model="gpt-4o",
    max_reflections=3
)

result = agent.run(
    "Напиши хайку о программировании",
    criteria=["5-7-5 слогов", "О коде", "Поэтические образы"]
)
```

## Связанное

- [Agents](agents.md)
- [Multi-Agent](multiagent.md)
- [Tools](tools.md)
