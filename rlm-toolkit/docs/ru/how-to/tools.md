# How-to: Создание инструментов

Рецепты создания пользовательских инструментов для агентов.

## Декоратор функции

```python
from rlm_toolkit.tools import Tool

@Tool(name="calculator", description="Вычислить математические выражения")
def calculator(expression: str) -> str:
    return str(eval(expression))
```

## С аннотациями типов

```python
from typing import Annotated
from rlm_toolkit.tools import Tool

@Tool(name="weather", description="Получить погоду для города")
def get_weather(
    city: Annotated[str, "Название города"],
    unit: Annotated[str, "celsius или fahrenheit"] = "celsius"
) -> str:
    return f"Погода в {city}: 22°{unit[0].upper()}"
```

## Класс-инструмент

```python
from rlm_toolkit.tools import BaseTool
from pydantic import BaseModel, Field

class SearchInput(BaseModel):
    query: str = Field(description="Поисковый запрос")
    max_results: int = Field(default=5, description="Макс. результатов")

class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Поиск информации в интернете"
    args_schema = SearchInput
    
    def run(self, query: str, max_results: int = 5) -> str:
        # Ваша логика поиска
        return f"Результаты для: {query}"
```

## Async инструмент

```python
import aiohttp
from rlm_toolkit.tools import Tool

@Tool(name="fetch_url", description="Получить контент по URL")
async def fetch_url(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()
```

## Инструмент с обработкой ошибок

```python
from rlm_toolkit.tools import Tool

@Tool(
    name="divide",
    description="Разделить два числа",
    handle_tool_error=True
)
def divide(a: float, b: float) -> str:
    if b == 0:
        raise ValueError("Нельзя делить на ноль")
    return str(a / b)
```

## Инструмент с прямым возвратом

```python
@Tool(
    name="final_answer",
    description="Вернуть финальный ответ пользователю",
    return_direct=True  # Пропустить обработку LLM
)
def final_answer(answer: str) -> str:
    return answer
```

## HTTP инструмент

```python
import requests
from rlm_toolkit.tools import Tool

@Tool(name="api_call", description="Вызвать API endpoint")
def api_call(endpoint: str, method: str = "GET") -> str:
    response = requests.request(method, endpoint)
    return response.text
```

## Инструмент базы данных

```python
import sqlite3
from rlm_toolkit.tools import Tool

@Tool(name="query_db", description="Запрос к базе данных")
def query_db(sql: str) -> str:
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(sql)
    results = cursor.fetchall()
    return str(results)
```

## Файловые инструменты

```python
from rlm_toolkit.tools import Tool

@Tool(name="read_file", description="Прочитать файл")
def read_file(path: str) -> str:
    with open(path, "r") as f:
        return f.read()

@Tool(name="write_file", description="Записать в файл")
def write_file(path: str, content: str) -> str:
    with open(path, "w") as f:
        f.write(content)
    return f"Записано в {path}"
```

## Инструмент со структурированным выводом

```python
from pydantic import BaseModel
from rlm_toolkit.tools import Tool

class Person(BaseModel):
    name: str
    age: int

@Tool(name="parse_person", description="Парсинг данных о человеке")
def parse_person(text: str) -> Person:
    # Логика парсинга
    return Person(name="Иван", age=30)
```

## Использование с агентом

```python
from rlm_toolkit.agents import ReActAgent

agent = ReActAgent.from_openai(
    "gpt-4o",
    tools=[calculator, get_weather, web_search]
)

result = agent.run("Что такое 25*4 и какая погода в Токио?")
```

## Связанное

- [Концепция: Агенты](../concepts/agents.md)
- [How-to: Агенты](./agents.md)
