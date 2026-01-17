# Agents

RLM-Toolkit provides a flexible agent system for autonomous task execution with tools.

## What are Agents?

Agents are LLM-powered systems that can:
- **Reason** about tasks
- **Plan** multi-step actions  
- **Use tools** to interact with the world
- **Iterate** until task completion

## Agent Types

| Type | Pattern | Use Case |
|------|---------|----------|
| **ReActAgent** | Reason + Act | General purpose |
| **PlanExecuteAgent** | Plan then execute | Complex tasks |
| **ToolAgent** | Direct tool use | Simple automation |
| **ConversationalAgent** | Chat + tools | Customer service |
| **SecureAgent** | With trust zones | Enterprise security |

## Basic Agent

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import Tool

# Define tools
@Tool(name="calculator", description="Calculate math expressions")
def calculator(expression: str) -> str:
    return str(eval(expression))

@Tool(name="search", description="Search the web")
def search(query: str) -> str:
    return f"Results for: {query}"

# Create agent
agent = ReActAgent.from_openai(
    model="gpt-4o",
    tools=[calculator, search]
)

# Run agent
result = agent.run("What is 25 * 4, then search for Python tutorials")
```

## ReAct Pattern

Reason and Act iteratively:

```
┌─────────────────────────────────────────────────────────────────┐
│                    ReAct Loop                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Input: "Calculate 25 * 4"                                      │
│                                                                  │
│  → Thought: I need to calculate 25 * 4                          │
│  → Action: calculator("25 * 4")                                 │
│  → Observation: 100                                             │
│  → Thought: I have the answer                                   │
│  → Final Answer: 25 * 4 = 100                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Built-in Tools

### Core Tools

```python
from rlm_toolkit.tools import (
    PythonREPL,         # Execute Python code
    ShellTool,          # Execute shell commands
    FileReader,         # Read files
    FileWriter,         # Write files
    WebSearchTool,      # Search the web
    HTTPTool,           # Make HTTP requests
    SQLTool,            # Execute SQL queries
    WikipediaTool,      # Query Wikipedia
    ArxivTool,          # Search arXiv papers
    CalculatorTool,     # Math calculations
)
```

### Using Tools

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import PythonREPL, WebSearchTool

agent = ReActAgent.from_openai(
    model="gpt-4o",
    tools=[
        PythonREPL(max_execution_time=30),
        WebSearchTool(provider="ddg")
    ]
)

result = agent.run(
    "Search for the current Bitcoin price, "
    "then write Python code to convert it to EUR"
)
```

## Custom Tools

### Function Decorator

```python
from rlm_toolkit.tools import Tool
from typing import Annotated

@Tool(
    name="get_weather",
    description="Get current weather for a city"
)
def get_weather(
    city: Annotated[str, "City name"],
    unit: Annotated[str, "Temperature unit (celsius/fahrenheit)"] = "celsius"
) -> str:
    # Your implementation
    return f"Weather in {city}: 22°{unit[0].upper()}"
```

### Class-based Tool

```python
from rlm_toolkit.tools import BaseTool
from pydantic import BaseModel, Field

class WeatherInput(BaseModel):
    city: str = Field(description="City name")
    unit: str = Field(default="celsius", description="Temperature unit")

class WeatherTool(BaseTool):
    name = "get_weather"
    description = "Get current weather for a city"
    args_schema = WeatherInput
    
    def run(self, city: str, unit: str = "celsius") -> str:
        return f"Weather in {city}: 22°{unit[0].upper()}"
```

## Plan-Execute Agent

For complex multi-step tasks:

```python
from rlm_toolkit.agents import PlanExecuteAgent

agent = PlanExecuteAgent.from_openai(
    model="gpt-4o",
    tools=[...],
    max_iterations=10
)

# Agent will:
# 1. Create a plan
# 2. Execute each step
# 3. Revise plan if needed
result = agent.run(
    "Research the top 5 Python web frameworks, "
    "compare their performance, and create a summary report"
)
```

## Agent with Memory

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.memory import HierarchicalMemory

memory = HierarchicalMemory(persist_directory="./agent_memory")

agent = ReActAgent.from_openai(
    model="gpt-4o",
    tools=[...],
    memory=memory
)

# Agent remembers previous interactions
agent.run("My name is Alex")
agent.run("What's my name?")  # "Your name is Alex"
```

## Secure Agents

```python
from rlm_toolkit.agents import SecureAgent, TrustZone
from rlm_toolkit.tools import SecurePythonREPL

# Secure code execution
secure_repl = SecurePythonREPL(
    allowed_imports=["math", "json", "datetime"],
    max_execution_time=5,
    enable_network=False,
    sandbox_mode=True
)

agent = SecureAgent(
    name="secure_processor",
    trust_zone=TrustZone(name="confidential", level=2),
    tools=[secure_repl],
    audit_enabled=True
)
```

## Streaming

```python
from rlm_toolkit.agents import ReActAgent

agent = ReActAgent.from_openai("gpt-4o", tools=[...])

# Stream thoughts and actions
for event in agent.stream("Analyze this data"):
    if event.type == "thought":
        print(f"Thinking: {event.content}")
    elif event.type == "action":
        print(f"Using tool: {event.tool_name}")
    elif event.type == "observation":
        print(f"Got: {event.content}")
    elif event.type == "final":
        print(f"Answer: {event.content}")
```

## Agent Configuration

```python
from rlm_toolkit.agents import ReActAgent, AgentConfig

config = AgentConfig(
    max_iterations=10,
    max_execution_time=300,  # seconds
    early_stopping=True,
    handle_parsing_errors=True,
    verbose=True,
    return_intermediate_steps=True
)

agent = ReActAgent.from_openai("gpt-4o", config=config, tools=[...])
```

## Error Handling

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.agents.exceptions import (
    AgentTimeoutError,
    MaxIterationsError,
    ToolExecutionError
)

try:
    result = agent.run("Complex task")
except AgentTimeoutError:
    print("Agent took too long")
except MaxIterationsError:
    print("Agent couldn't complete in allowed iterations")
except ToolExecutionError as e:
    print(f"Tool {e.tool_name} failed: {e.error}")
```

## Best Practices

!!! tip "Tool Design"
    - Keep tools focused and single-purpose
    - Provide clear descriptions
    - Use type hints for parameters

!!! tip "Prompt Engineering"
    - Give clear task descriptions
    - Include examples when needed
    - Specify constraints upfront

!!! tip "Safety"
    - Limit tool permissions
    - Set execution timeouts
    - Use SecureAgent for untrusted input

!!! tip "Debugging"
    - Enable verbose mode
    - Return intermediate steps
    - Use streaming to see process

## Related

- [Tutorial: Agents](../tutorials/04-agents.md)
- [Tutorial: Multi-Agent](../tutorials/09-multiagent.md)
- [Concept: Security](./security.md)
- [Concept: Multi-Agent](./multiagent.md)
