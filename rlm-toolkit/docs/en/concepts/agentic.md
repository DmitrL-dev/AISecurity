# Agentic Workflows

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **High-level agentic patterns** for complex tasks

## Overview

The `agentic` module provides workflows:
- **Plan-and-Execute** — Multi-step planning
- **ReAct** — Reasoning + Acting
- **Reflection** — Self-critique & improvement
- **Multi-turn** — Conversation management

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
Research the top 5 companies by market cap
and create a chart comparing their growth.
""")

print(result.plan)    # Step-by-step plan
print(result.output)  # Final result
```

## ReAct

```python
from rlm_toolkit.agentic import ReActAgent

agent = ReActAgent(
    model="gpt-4o",
    tools=[WebSearchTool()],
    max_iterations=5
)

result = agent.run("What was the highest temperature ever recorded in Death Valley?")
# Thought: I need to search for temperature records
# Action: web_search("highest temperature Death Valley")
# Observation: 134°F (56.7°C) on July 10, 1913
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
    "Write a haiku about programming",
    criteria=["5-7-5 syllables", "About coding", "Poetic imagery"]
)
```

## Related

- [Agents](agents.md)
- [Multi-Agent](multiagent.md)
- [Tools](tools.md)
