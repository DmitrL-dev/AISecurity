# Tutorial 4: Agents

Build intelligent agents that can use tools, make decisions, and accomplish complex tasks.

## What You'll Build

An agent that:

1. Uses multiple tools (search, calculator, code executor)
2. Reasons about which tool to use
3. Handles multi-step tasks
4. Maintains context across interactions

## Understanding Agents

```
┌─────────────────────────────────────────────────────────────────┐
│                        Agent Loop                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   User Query → Agent → Think → Choose Tool → Execute → Observe   │
│                   ↑                                     ↓        │
│                   └─────────────────────────────────────┘        │
│                          (repeat until done)                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

```bash
pip install rlm-toolkit[all]
export OPENAI_API_KEY=your-key
```

## Step 1: Simple Agent with Tools

```python
from rlm_toolkit import RLM
from rlm_toolkit.tools import Tool, Calculator, WebSearch

# Define custom tool
@Tool(name="get_weather", description="Get current weather for a city")
def get_weather(city: str) -> str:
    """Simulated weather API."""
    return f"Weather in {city}: 22°C, partly cloudy"

# Create agent with tools
rlm = RLM.from_openai(
    "gpt-4o",
    tools=[Calculator(), WebSearch(), get_weather]
)

# Agent will choose appropriate tool
result = rlm.run("What's 15% of 340 plus the current temperature in Tokyo?")
print(result.final_answer)
```

## Step 2: Built-in Tools

RLM-Toolkit includes 35+ pre-built tools:

```python
from rlm_toolkit.tools import (
    Calculator,           # Math operations
    WebSearch,           # Search the web
    WikipediaSearch,     # Search Wikipedia
    PythonREPL,          # Execute Python code (sandboxed)
    FileReader,          # Read files
    FileWriter,          # Write files
    SQLQuery,            # Query databases
    APIRequest,          # Make HTTP requests
    JSONParser,          # Parse JSON
    DateTimeTool,        # Date/time operations
)

# Create agent with multiple tools
rlm = RLM.from_openai(
    "gpt-4o",
    tools=[
        Calculator(),
        WebSearch(max_results=5),
        PythonREPL(sandbox=True),
        DateTimeTool(),
    ]
)
```

## Step 3: Custom Tools

Create your own tools with decorators:

```python
from rlm_toolkit.tools import Tool
from typing import List

@Tool(
    name="search_products",
    description="Search for products in the database",
    args_schema={
        "query": {"type": "string", "description": "Search query"},
        "max_results": {"type": "integer", "description": "Max results", "default": 10}
    }
)
def search_products(query: str, max_results: int = 10) -> List[dict]:
    """Search products in database."""
    # Your implementation here
    return [{"name": "Product 1", "price": 99.99}]

@Tool(
    name="create_order",
    description="Create a new order for a customer"
)
def create_order(customer_id: str, product_ids: List[str]) -> dict:
    """Create order in system."""
    return {"order_id": "ORD-12345", "status": "created"}
```

## Step 4: Tool Classes

For complex tools, use classes:

```python
from rlm_toolkit.tools import BaseTool
from pydantic import BaseModel, Field

class DatabaseQueryInput(BaseModel):
    query: str = Field(description="SQL query to execute")
    database: str = Field(default="main", description="Database name")

class DatabaseQueryTool(BaseTool):
    name = "database_query"
    description = "Execute SQL queries on the database"
    args_schema = DatabaseQueryInput
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
    
    def _run(self, query: str, database: str = "main") -> str:
        # Execute query
        import sqlalchemy
        engine = sqlalchemy.create_engine(self.connection_string)
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text(query))
            return str(result.fetchall())

# Use the tool
db_tool = DatabaseQueryTool("postgresql://localhost/mydb")
rlm = RLM.from_openai("gpt-4o", tools=[db_tool])
```

## Step 5: Agent with Memory

Agents can maintain context:

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import HierarchicalMemory
from rlm_toolkit.tools import Calculator, WebSearch

# Create agent with memory
memory = HierarchicalMemory()

rlm = RLM.from_openai(
    "gpt-4o",
    memory=memory,
    tools=[Calculator(), WebSearch()]
)

# Multi-turn conversation
rlm.run("Search for the population of France")
rlm.run("Now calculate what 15% of that is")  # Remembers previous result
```

## Step 6: ReAct Agent Pattern

The ReAct pattern: Reason + Act:

```python
from rlm_toolkit import RLM, RLMConfig

config = RLMConfig(
    agent_type="react",
    max_iterations=10,
    verbose=True  # Show reasoning steps
)

rlm = RLM.from_openai(
    "gpt-4o",
    config=config,
    tools=[Calculator(), WebSearch(), PythonREPL()]
)

result = rlm.run(
    "Find the current stock price of Apple, calculate 20% increase, "
    "and format it as a Python dictionary"
)

# Shows reasoning:
# Thought: I need to find Apple's stock price
# Action: WebSearch("Apple stock price")
# Observation: $178.50
# Thought: Now calculate 20% increase
# Action: Calculator("178.50 * 1.20")
# Observation: 214.20
# Thought: Format as Python dict
# Action: PythonREPL("print({'current': 178.50, 'increased': 214.20})")
# Final Answer: {'current': 178.50, 'increased': 214.20}
```

## Step 7: Secure Code Execution

Use CIRCLE-compliant sandbox for code execution:

```python
from rlm_toolkit.tools import SecurePythonREPL

# Sandboxed execution with restrictions
secure_repl = SecurePythonREPL(
    allowed_imports=["math", "json", "datetime"],
    max_execution_time=5,  # seconds
    max_memory_mb=100,
    enable_network=False
)

rlm = RLM.from_openai("gpt-4o", tools=[secure_repl])
result = rlm.run("Write Python code to calculate fibonacci(20)")
```

## Complete Agent Application

```python
# agent_app.py
from rlm_toolkit import RLM, RLMConfig
from rlm_toolkit.memory import HierarchicalMemory
from rlm_toolkit.tools import (
    Calculator,
    WebSearch,
    SecurePythonREPL,
    DateTimeTool,
    Tool
)

# Custom tools
@Tool(name="send_email", description="Send an email")
def send_email(to: str, subject: str, body: str) -> str:
    # Simulated
    return f"Email sent to {to}"

@Tool(name="create_reminder", description="Create a reminder")
def create_reminder(message: str, when: str) -> str:
    return f"Reminder set: '{message}' at {when}"

def create_assistant():
    """Create a capable AI assistant."""
    
    memory = HierarchicalMemory(
        persist_directory="./assistant_memory"
    )
    
    config = RLMConfig(
        agent_type="react",
        max_iterations=15,
        verbose=False
    )
    
    tools = [
        Calculator(),
        WebSearch(max_results=3),
        SecurePythonREPL(allowed_imports=["math", "json"]),
        DateTimeTool(),
        send_email,
        create_reminder,
    ]
    
    system_prompt = """You are a helpful AI assistant with access to various tools.
    Use tools when needed to provide accurate information.
    Think step by step before acting.
    Always provide clear, concise answers."""
    
    return RLM.from_openai(
        "gpt-4o",
        config=config,
        memory=memory,
        tools=tools,
        system_prompt=system_prompt
    )

def main():
    print("="*50)
    print("🤖 AI Assistant")
    print("   Commands: 'quit', 'tools', 'history'")
    print("="*50)
    
    agent = create_assistant()
    
    while True:
        user_input = input("\n👤 You: ").strip()
        
        if not user_input:
            continue
        
        if user_input == 'quit':
            break
        
        if user_input == 'tools':
            print("Available tools:")
            for tool in agent.tools:
                print(f"  - {tool.name}: {tool.description}")
            continue
        
        if user_input == 'history':
            for msg in agent.memory.get_recent(5):
                print(f"  {msg}")
            continue
        
        result = agent.run(user_input)
        print(f"\n🤖 Assistant: {result.final_answer}")
        
        if result.tool_calls:
            print(f"\n📎 Tools used: {[t.name for t in result.tool_calls]}")

if __name__ == "__main__":
    main()
```

## Agent Best Practices

!!! tip "Tool Selection"
    Provide clear, distinct tool descriptions to help the agent choose correctly.

!!! tip "Error Handling"
    Tools should return helpful error messages:
    ```python
    @Tool(name="api_call")
    def api_call(endpoint: str) -> str:
        try:
            response = requests.get(endpoint)
            return response.json()
        except Exception as e:
            return f"Error: {str(e)}. Try a different endpoint."
    ```

!!! tip "Iteration Limits"
    Set reasonable limits to prevent infinite loops:
    ```python
    config = RLMConfig(max_iterations=10)
    ```

!!! warning "Security"
    Always sandbox code execution tools:
    ```python
    SecurePythonREPL(sandbox=True, enable_network=False)
    ```

## Next Steps

- [Tutorial 5: Memory Systems](05-memory.md)
- [Tutorial 9: Multi-Agent](09-multiagent.md)
- [Concept: Agents](../concepts/agents.md)
