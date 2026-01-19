# Tools

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **Инструменты агентов** для взаимодействия с миром

## Обзор

Tools позволяют RLM агентам:
- Выполнять код (Python, Shell)
- Искать в интернете
- Запрашивать базы данных
- Вызывать API
- Работать с файловой системой

## Быстрый старт

```python
from rlm_toolkit.tools import WebSearchTool, PythonREPL
from rlm_toolkit.agents import Agent

# Создаём инструменты
tools = [
    WebSearchTool(),
    PythonREPL()
]

# Создаём агента с инструментами
agent = Agent(
    model="gpt-4o",
    tools=tools
)

# Агент теперь может искать и выполнять код
result = agent.run("Найди последнюю версию Python и вычисли дней с релиза")
```

## Встроенные инструменты

### Веб-поиск

```python
from rlm_toolkit.tools import WebSearchTool

search = WebSearchTool(
    engine="google",  # или "bing", "duckduckgo"
    max_results=5
)

results = search.run("RLM-Toolkit документация")
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
print(f"Сегодня {today}")
""")
```

### Безопасный Python REPL (CIRCLE)

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

### SQL запрос

```python
from rlm_toolkit.tools import SQLQueryTool

sql = SQLQueryTool(
    connection_string="postgresql://localhost/mydb",
    read_only=True,
    max_rows=100
)

result = sql.run("SELECT name, email FROM users LIMIT 10")
```

### API вызов

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

### Файловые операции

```python
from rlm_toolkit.tools import FileReadTool, FileWriteTool

reader = FileReadTool(allowed_paths=["./data/*"])
writer = FileWriteTool(allowed_paths=["./output/*"])

content = reader.run("./data/input.json")
writer.run("./output/result.json", processed_content)
```

## Кастомные Tools

### Простой Function Tool

```python
from rlm_toolkit.tools import tool

@tool
def calculate_discount(price: float, discount_percent: float) -> float:
    """Вычислить цену со скидкой."""
    return price * (1 - discount_percent / 100)

# Использование в агенте
agent = Agent(tools=[calculate_discount])
```

### Class-based Tool

```python
from rlm_toolkit.tools import BaseTool

class WeatherTool(BaseTool):
    name = "get_weather"
    description = "Получить текущую погоду для города"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def _run(self, city: str) -> dict:
        # Вызов API погоды
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

## Разрешения инструментов

### Trust Zones

```python
from rlm_toolkit.tools import PythonREPL
from rlm_toolkit.security import TrustZone

# Ограниченный инструмент
repl = PythonREPL(
    trust_zone=TrustZone(name="sandbox", level=0),
    capabilities=["math", "string"]
)

# Привилегированный инструмент
privileged_repl = PythonREPL(
    trust_zone=TrustZone(name="internal", level=2),
    capabilities=["network", "filesystem"]
)
```

## Примеры

### Исследовательский агент

```python
from rlm_toolkit.tools import WebSearchTool, PythonREPL
from rlm_toolkit.agents import Agent

agent = Agent(
    model="gpt-4o",
    tools=[
        WebSearchTool(),
        PythonREPL()
    ],
    system_prompt="Ты исследовательский ассистент"
)

result = agent.run("""
Исследуй топ-5 языков программирования по популярности в 2026
и создай диаграмму визуализации.
""")
```

### Дата-пайплайн

```python
from rlm_toolkit.tools import SQLQueryTool, PythonREPL, FileWriteTool

tools = [
    SQLQueryTool(connection_string="..."),
    PythonREPL(allowed_imports=["pandas", "json"]),
    FileWriteTool(allowed_paths=["./reports/*"])
]

agent = Agent(model="gpt-4o", tools=tools)
agent.run("Запроси таблицу users, проанализируй демографию, сохрани отчёт в CSV")
```

## Связанное

- [Agents](agents.md)
- [Security](security.md)
- [Туториал: Agents](../tutorials/04-agents.md)
