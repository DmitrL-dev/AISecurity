# How-to: Use Agents

Recipes for building and configuring agents.

## Create a Simple Agent

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import Tool

@Tool(name="calculator")
def calc(expression: str) -> str:
    return str(eval(expression))

agent = ReActAgent.from_openai("gpt-4o", tools=[calc])
result = agent.run("What is 25 * 4?")
```

## Add Multiple Tools

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

## Configure Agent Limits

```python
from rlm_toolkit.agents import AgentConfig

config = AgentConfig(
    max_iterations=10,
    max_execution_time=300,
    verbose=True
)

agent = ReActAgent.from_openai("gpt-4o", config=config, tools=[...])
```

## Use Plan-Execute Agent

```python
from rlm_toolkit.agents import PlanExecuteAgent

agent = PlanExecuteAgent.from_openai(
    "gpt-4o",
    tools=[...],
    max_iterations=10
)

result = agent.run("Research Python frameworks and compare them")
```

## Agent with Memory

```python
from rlm_toolkit.memory import HierarchicalMemory

memory = HierarchicalMemory(persist_directory="./memory")
agent = ReActAgent.from_openai("gpt-4o", memory=memory, tools=[...])
```

## Stream Agent Output

```python
for event in agent.stream("Analyze data"):
    if event.type == "thought":
        print(f"Thinking: {event.content}")
    elif event.type == "action":
        print(f"Tool: {event.tool_name}")
    elif event.type == "final":
        print(f"Answer: {event.content}")
```

## Secure Agent

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

## Custom Tool

```python
from rlm_toolkit.tools import Tool
from typing import Annotated

@Tool(name="weather", description="Get weather for a city")
def get_weather(
    city: Annotated[str, "City name"]
) -> str:
    return f"Weather in {city}: 22°C"
```

## Related

- [Concept: Agents](../concepts/agents.md)
- [Tutorial: Agents](../tutorials/04-agents.md)
