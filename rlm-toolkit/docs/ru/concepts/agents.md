# Агенты

RLM-Toolkit предоставляет гибкую систему агентов для автономного выполнения задач с инструментами.

## Что такое агенты?

Агенты — это LLM-powered системы, которые могут:
- **Рассуждать** о задачах
- **Планировать** многоэтапные действия  
- **Использовать инструменты** для взаимодействия с миром
- **Итерировать** до завершения задачи

## Типы агентов

| Тип | Паттерн | Применение |
|-----|---------|------------|
| **ReActAgent** | Reason + Act | Общего назначения |
| **PlanExecuteAgent** | Планирование затем выполнение | Сложные задачи |
| **ToolAgent** | Прямое использование инструментов | Простая автоматизация |
| **ConversationalAgent** | Чат + инструменты | Клиентский сервис |
| **SecureAgent** | С зонами доверия | Enterprise безопасность |

## Базовый агент

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import Tool

# Определение инструментов
@Tool(name="calculator", description="Вычислить математические выражения")
def calculator(expression: str) -> str:
    return str(eval(expression))

@Tool(name="search", description="Поиск в интернете")
def search(query: str) -> str:
    return f"Результаты для: {query}"

# Создание агента
agent = ReActAgent.from_openai(
    model="gpt-4o",
    tools=[calculator, search]
)

# Запуск агента
result = agent.run("Что такое 25 * 4, затем найди туториалы по Python")
```

## Паттерн ReAct

Итеративные рассуждения и действия:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Цикл ReAct                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Input: "Вычислить 25 * 4"                                      │
│                                                                  │
│  → Thought: Мне нужно вычислить 25 * 4                          │
│  → Action: calculator("25 * 4")                                 │
│  → Observation: 100                                             │
│  → Thought: У меня есть ответ                                   │
│  → Final Answer: 25 * 4 = 100                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Встроенные инструменты

### Основные инструменты

```python
from rlm_toolkit.tools import (
    PythonREPL,         # Выполнение Python кода
    ShellTool,          # Выполнение shell команд
    FileReader,         # Чтение файлов
    FileWriter,         # Запись файлов
    WebSearchTool,      # Поиск в интернете
    HTTPTool,           # HTTP запросы
    SQLTool,            # Выполнение SQL запросов
    WikipediaTool,      # Запросы к Wikipedia
    ArxivTool,          # Поиск статей arXiv
    CalculatorTool,     # Математические вычисления
)
```

### Использование инструментов

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
    "Найди текущий курс Bitcoin, "
    "затем напиши Python код для конвертации в EUR"
)
```

## Пользовательские инструменты

### Декоратор функции

```python
from rlm_toolkit.tools import Tool
from typing import Annotated

@Tool(
    name="get_weather",
    description="Получить текущую погоду для города"
)
def get_weather(
    city: Annotated[str, "Название города"],
    unit: Annotated[str, "Единица температуры (celsius/fahrenheit)"] = "celsius"
) -> str:
    # Ваша реализация
    return f"Погода в {city}: 22°{unit[0].upper()}"
```

### Класс-инструмент

```python
from rlm_toolkit.tools import BaseTool
from pydantic import BaseModel, Field

class WeatherInput(BaseModel):
    city: str = Field(description="Название города")
    unit: str = Field(default="celsius", description="Единица температуры")

class WeatherTool(BaseTool):
    name = "get_weather"
    description = "Получить текущую погоду для города"
    args_schema = WeatherInput
    
    def run(self, city: str, unit: str = "celsius") -> str:
        return f"Погода в {city}: 22°{unit[0].upper()}"
```

## План-Выполнение Агент

Для сложных многоэтапных задач:

```python
from rlm_toolkit.agents import PlanExecuteAgent

agent = PlanExecuteAgent.from_openai(
    model="gpt-4o",
    tools=[...],
    max_iterations=10
)

# Агент будет:
# 1. Создать план
# 2. Выполнить каждый шаг
# 3. Пересмотреть план при необходимости
result = agent.run(
    "Исследуй топ-5 Python веб-фреймворков, "
    "сравни их производительность и создай отчёт"
)
```

## Агент с памятью

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.memory import HierarchicalMemory

memory = HierarchicalMemory(persist_directory="./agent_memory")

agent = ReActAgent.from_openai(
    model="gpt-4o",
    tools=[...],
    memory=memory
)

# Агент помнит предыдущие взаимодействия
agent.run("Меня зовут Алексей")
agent.run("Как меня зовут?")  # "Вас зовут Алексей"
```

## Безопасные агенты

```python
from rlm_toolkit.agents import SecureAgent, TrustZone
from rlm_toolkit.tools import SecurePythonREPL

# Безопасное выполнение кода
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

# Стриминг мыслей и действий
for event in agent.stream("Проанализируй эти данные"):
    if event.type == "thought":
        print(f"Думает: {event.content}")
    elif event.type == "action":
        print(f"Использует инструмент: {event.tool_name}")
    elif event.type == "observation":
        print(f"Получил: {event.content}")
    elif event.type == "final":
        print(f"Ответ: {event.content}")
```

## Конфигурация агента

```python
from rlm_toolkit.agents import ReActAgent, AgentConfig

config = AgentConfig(
    max_iterations=10,
    max_execution_time=300,  # секунд
    early_stopping=True,
    handle_parsing_errors=True,
    verbose=True,
    return_intermediate_steps=True
)

agent = ReActAgent.from_openai("gpt-4o", config=config, tools=[...])
```

## Обработка ошибок

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.agents.exceptions import (
    AgentTimeoutError,
    MaxIterationsError,
    ToolExecutionError
)

try:
    result = agent.run("Сложная задача")
except AgentTimeoutError:
    print("Агент работал слишком долго")
except MaxIterationsError:
    print("Агент не смог завершить за разрешённые итерации")
except ToolExecutionError as e:
    print(f"Инструмент {e.tool_name} упал: {e.error}")
```

## Лучшие практики

!!! tip "Дизайн инструментов"
    - Делайте инструменты фокусированными и однозадачными
    - Предоставляйте чёткие описания
    - Используйте type hints для параметров

!!! tip "Prompt Engineering"
    - Давайте чёткие описания задач
    - Включайте примеры при необходимости
    - Указывайте ограничения заранее

!!! tip "Безопасность"
    - Ограничивайте права инструментов
    - Устанавливайте таймауты выполнения
    - Используйте SecureAgent для ненадёжного ввода

!!! tip "Отладка"
    - Включите verbose режим
    - Возвращайте промежуточные шаги
    - Используйте streaming для просмотра процесса

## Связанное

- [Туториал: Агенты](../tutorials/04-agents.md)
- [Туториал: Multi-Agent](../tutorials/09-multiagent.md)
- [Концепция: Безопасность](./security.md)
- [Концепция: Multi-Agent](./multiagent.md)
