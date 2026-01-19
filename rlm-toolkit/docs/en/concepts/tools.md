# Tools

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **Agent tools** for interacting with the world

## Overview

Tools enable RLM agents to:
- Execute code (Python, Shell)
- Search the web
- Query databases
- Call APIs
- Access file systems

## Quick Start

```python
from rlm_toolkit.tools import WebSearchTool, PythonREPL
from rlm_toolkit.agents import Agent

# Create tools
tools = [
    WebSearchTool(),
    PythonREPL()
]

# Create agent with tools
agent = Agent(
    model="gpt-4o",
    tools=tools
)

# Agent can now search and execute code
result = agent.run("Search for latest Python version and calculate days since release")
```

## Built-in Tools

### Web Search

```python
from rlm_toolkit.tools import WebSearchTool

search = WebSearchTool(
    engine="google",  # or "bing", "duckduckgo"
    max_results=5
)

results = search.run("RLM-Toolkit documentation")
```

### Python REPL

```python
from rlm_toolkit.tools import PythonREPL

repl = PythonREPL(
    allowed_imports=["math", "json", "datetime"],
    max_execution_time=30,
    persist_session=True
)

result = repl.run("""
import datetime
today = datetime.date.today()
print(f"Today is {today}")
""")
```

### Secure Python REPL (CIRCLE)

```python
from rlm_toolkit.tools import SecurePythonREPL

repl = SecurePythonREPL(
    allowed_imports=["math", "json"],
    enable_network=False,
    enable_filesystem=False,
    max_memory_mb=256
)
```

### Shell

```python
from rlm_toolkit.tools import ShellTool

shell = ShellTool(
    allowed_commands=["ls", "cat", "grep"],
    working_directory="/safe/path"
)

result = shell.run("ls -la")
```

### SQL Query

```python
from rlm_toolkit.tools import SQLQueryTool

sql = SQLQueryTool(
    connection_string="postgresql://localhost/mydb",
    read_only=True,
    max_rows=100
)

result = sql.run("SELECT name, email FROM users LIMIT 10")
```

### API Call

```python
from rlm_toolkit.tools import APITool

api = APITool(
    base_url="https://api.example.com",
    headers={"Authorization": "Bearer ..."},
    timeout=30
)

result = api.run(
    method="GET",
    endpoint="/users",
    params={"limit": 10}
)
```

### File Operations

```python
from rlm_toolkit.tools import FileReadTool, FileWriteTool

reader = FileReadTool(allowed_paths=["./data/*"])
writer = FileWriteTool(allowed_paths=["./output/*"])

content = reader.run("./data/input.json")
writer.run("./output/result.json", processed_content)
```

## Custom Tools

### Simple Function Tool

```python
from rlm_toolkit.tools import tool

@tool
def calculate_discount(price: float, discount_percent: float) -> float:
    """Calculate discounted price."""
    return price * (1 - discount_percent / 100)

# Use in agent
agent = Agent(tools=[calculate_discount])
```

### Class-based Tool

```python
from rlm_toolkit.tools import BaseTool

class WeatherTool(BaseTool):
    name = "get_weather"
    description = "Get current weather for a city"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def _run(self, city: str) -> dict:
        # Call weather API
        response = requests.get(
            f"https://api.weather.com/v1/current?city={city}",
            headers={"Authorization": self.api_key}
        )
        return response.json()

weather = WeatherTool(api_key="...")
```

### Async Tool

```python
from rlm_toolkit.tools import BaseTool

class AsyncAPITool(BaseTool):
    name = "async_api"
    
    async def _arun(self, query: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.example.com/search?q={query}") as resp:
                return await resp.text()
```

## Tool Permissions

### Trust Zones

```python
from rlm_toolkit.tools import PythonREPL
from rlm_toolkit.security import TrustZone

# Restricted tool
repl = PythonREPL(
    trust_zone=TrustZone(name="sandbox", level=0),
    capabilities=["math", "string"]
)

# Elevated tool
privileged_repl = PythonREPL(
    trust_zone=TrustZone(name="internal", level=2),
    capabilities=["network", "filesystem"]
)
```

## Examples

### Research Agent

```python
from rlm_toolkit.tools import WebSearchTool, PythonREPL
from rlm_toolkit.agents import Agent

agent = Agent(
    model="gpt-4o",
    tools=[
        WebSearchTool(),
        PythonREPL()
    ],
    system_prompt="You are a research assistant"
)

result = agent.run("""
Research the top 5 programming languages by popularity in 2026
and create a visualization chart.
""")
```

### Data Pipeline

```python
from rlm_toolkit.tools import SQLQueryTool, PythonREPL, FileWriteTool

tools = [
    SQLQueryTool(connection_string="..."),
    PythonREPL(allowed_imports=["pandas", "json"]),
    FileWriteTool(allowed_paths=["./reports/*"])
]

agent = Agent(model="gpt-4o", tools=tools)
agent.run("Query users table, analyze demographics, save report to CSV")
```

## Related

- [Agents](agents.md)
- [Security](security.md)
- [Tutorial: Agents](../tutorials/04-agents.md)
