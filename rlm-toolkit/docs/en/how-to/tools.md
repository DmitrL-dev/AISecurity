# How-to: Create Tools

Recipes for building custom tools for agents.

## Function Decorator

```python
from rlm_toolkit.tools import Tool

@Tool(name="calculator", description="Calculate math expressions")
def calculator(expression: str) -> str:
    return str(eval(expression))
```

## With Type Annotations

```python
from typing import Annotated
from rlm_toolkit.tools import Tool

@Tool(name="weather", description="Get weather for a city")
def get_weather(
    city: Annotated[str, "City name"],
    unit: Annotated[str, "celsius or fahrenheit"] = "celsius"
) -> str:
    return f"Weather in {city}: 22°{unit[0].upper()}"
```

## Class-Based Tool

```python
from rlm_toolkit.tools import BaseTool
from pydantic import BaseModel, Field

class SearchInput(BaseModel):
    query: str = Field(description="Search query")
    max_results: int = Field(default=5, description="Max results")

class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search the web for information"
    args_schema = SearchInput
    
    def run(self, query: str, max_results: int = 5) -> str:
        # Your search logic
        return f"Results for: {query}"
```

## Async Tool

```python
import aiohttp
from rlm_toolkit.tools import Tool

@Tool(name="fetch_url", description="Fetch content from URL")
async def fetch_url(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()
```

## Tool with Error Handling

```python
from rlm_toolkit.tools import Tool

@Tool(
    name="divide",
    description="Divide two numbers",
    handle_tool_error=True
)
def divide(a: float, b: float) -> str:
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return str(a / b)
```

## Tool with Return Direct

```python
@Tool(
    name="final_answer",
    description="Return final answer to user",
    return_direct=True  # Skip LLM processing of output
)
def final_answer(answer: str) -> str:
    return answer
```

## HTTP Tool

```python
import requests
from rlm_toolkit.tools import Tool

@Tool(name="api_call", description="Call an API endpoint")
def api_call(endpoint: str, method: str = "GET") -> str:
    response = requests.request(method, endpoint)
    return response.text
```

## Database Tool

```python
import sqlite3
from rlm_toolkit.tools import Tool

@Tool(name="query_db", description="Query the database")
def query_db(sql: str) -> str:
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(sql)
    results = cursor.fetchall()
    return str(results)
```

## File Tools

```python
from rlm_toolkit.tools import Tool

@Tool(name="read_file", description="Read a file")
def read_file(path: str) -> str:
    with open(path, "r") as f:
        return f.read()

@Tool(name="write_file", description="Write to a file")
def write_file(path: str, content: str) -> str:
    with open(path, "w") as f:
        f.write(content)
    return f"Written to {path}"
```

## Structured Output Tool

```python
from pydantic import BaseModel
from rlm_toolkit.tools import Tool

class Person(BaseModel):
    name: str
    age: int

@Tool(name="parse_person", description="Parse person data")
def parse_person(text: str) -> Person:
    # Parse logic
    return Person(name="John", age=30)
```

## Use with Agent

```python
from rlm_toolkit.agents import ReActAgent

agent = ReActAgent.from_openai(
    "gpt-4o",
    tools=[calculator, get_weather, web_search]
)

result = agent.run("What is 25*4 and what's the weather in Tokyo?")
```

## Related

- [Concept: Agents](../concepts/agents.md)
- [How-to: Agents](./agents.md)
