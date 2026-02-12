# Туториал 4: Агенты

Создавайте интеллектуальных агентов, которые используют инструменты, принимают решения и выполняют сложные задачи.

## Что вы создадите

Агента, который:

1. Использует несколько инструментов (поиск, калькулятор, исполнитель кода)
2. Рассуждает о том, какой инструмент использовать
3. Обрабатывает многошаговые задачи
4. Сохраняет контекст между взаимодействиями

## Понимание агентов

```
┌─────────────────────────────────────────────────────────────────┐
│                        Цикл агента                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Запрос → Агент → Размышление → Выбор инструмента → Выполнение → Наблюдение │
│                   ↑                                     ↓        │
│                   └─────────────────────────────────────┘        │
│                          (повторять до завершения)               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Предварительные требования

```bash
pip install rlm-toolkit[all]
export OPENAI_API_KEY=your-key
```

## Шаг 1: Простой агент с инструментами

```python
from rlm_toolkit import RLM
from rlm_toolkit.tools import Tool, Calculator, WebSearch

# Определяем пользовательский инструмент
@Tool(name="get_weather", description="Получить текущую погоду для города")
def get_weather(city: str) -> str:
    """Симулированный API погоды."""
    return f"Погода в {city}: 22°C, переменная облачность"

# Создаём агента с инструментами
rlm = RLM.from_openai(
    "gpt-4o",
    tools=[Calculator(), WebSearch(), get_weather]
)

# Агент выберет подходящий инструмент
result = rlm.run("Сколько будет 15% от 340 плюс текущая температура в Токио?")
print(result.answer)
```

## Шаг 2: Встроенные инструменты

RLM-Toolkit включает 35+ готовых инструментов:

```python
from rlm_toolkit.tools import (
    Calculator,           # Математические операции
    WebSearch,           # Поиск в интернете
    WikipediaSearch,     # Поиск в Википедии
    PythonREPL,          # Выполнение Python кода (в песочнице)
    FileReader,          # Чтение файлов
    FileWriter,          # Запись файлов
    SQLQuery,            # Запросы к базам данных
    APIRequest,          # HTTP-запросы
    JSONParser,          # Парсинг JSON
    DateTimeTool,        # Операции с датой и временем
)

# Создаём агента с несколькими инструментами
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

## Шаг 3: Пользовательские инструменты

Создавайте собственные инструменты с декораторами:

```python
from rlm_toolkit.tools import Tool
from typing import List

@Tool(
    name="search_products",
    description="Поиск товаров в базе данных",
    args_schema={
        "query": {"type": "string", "description": "Поисковый запрос"},
        "max_results": {"type": "integer", "description": "Максимум результатов", "default": 10}
    }
)
def search_products(query: str, max_results: int = 10) -> List[dict]:
    """Поиск товаров в базе данных."""
    # Ваша реализация здесь
    return [{"name": "Товар 1", "price": 99.99}]

@Tool(
    name="create_order",
    description="Создать новый заказ для клиента"
)
def create_order(customer_id: str, product_ids: List[str]) -> dict:
    """Создание заказа в системе."""
    return {"order_id": "ORD-12345", "status": "создан"}
```

## Шаг 4: Классы инструментов

Для сложных инструментов используйте классы:

```python
from rlm_toolkit.tools import BaseTool
from pydantic import BaseModel, Field

class DatabaseQueryInput(BaseModel):
    query: str = Field(description="SQL-запрос для выполнения")
    database: str = Field(default="main", description="Имя базы данных")

class DatabaseQueryTool(BaseTool):
    name = "database_query"
    description = "Выполнение SQL-запросов к базе данных"
    args_schema = DatabaseQueryInput
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
    
    def _run(self, query: str, database: str = "main") -> str:
        # Выполнение запроса
        import sqlalchemy
        engine = sqlalchemy.create_engine(self.connection_string)
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text(query))
            return str(result.fetchall())

# Используем инструмент
db_tool = DatabaseQueryTool("postgresql://localhost/mydb")
rlm = RLM.from_openai("gpt-4o", tools=[db_tool])
```

## Шаг 5: Агент с памятью

Агенты могут сохранять контекст:

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import HierarchicalMemory
from rlm_toolkit.tools import Calculator, WebSearch

# Создаём агента с памятью
memory = HierarchicalMemory()

rlm = RLM.from_openai(
    "gpt-4o",
    memory=memory,
    tools=[Calculator(), WebSearch()]
)

# Многоходовой разговор
rlm.run("Найди население Франции")
rlm.run("Теперь посчитай 15% от этого")  # Помнит предыдущий результат
```

## Шаг 6: Паттерн ReAct агента

Паттерн ReAct: Рассуждение + Действие:

```python
from rlm_toolkit import RLM, RLMConfig

config = RLMConfig(
    agent_type="react",
    max_iterations=10,
    verbose=True  # Показывать шаги рассуждения
)

rlm = RLM.from_openai(
    "gpt-4o",
    config=config,
    tools=[Calculator(), WebSearch(), PythonREPL()]
)

result = rlm.run(
    "Найди текущую цену акций Apple, рассчитай увеличение на 20%, "
    "и отформатируй как Python словарь"
)

# Показывает рассуждение:
# Мысль: Мне нужно найти цену акций Apple
# Действие: WebSearch("Apple stock price")
# Наблюдение: $178.50
# Мысль: Теперь рассчитаю увеличение на 20%
# Действие: Calculator("178.50 * 1.20")
# Наблюдение: 214.20
# Мысль: Отформатирую как Python словарь
# Действие: PythonREPL("print({'current': 178.50, 'increased': 214.20})")
# Финальный ответ: {'current': 178.50, 'increased': 214.20}
```

## Шаг 7: Безопасное выполнение кода

Используйте CIRCLE-совместимую песочницу для выполнения кода:

```python
from rlm_toolkit.tools import SecurePythonREPL

# Выполнение в песочнице с ограничениями
secure_repl = SecurePythonREPL(
    allowed_imports=["math", "json", "datetime"],
    max_execution_time=5,  # секунд
    max_memory_mb=100,
    enable_network=False
)

rlm = RLM.from_openai("gpt-4o", tools=[secure_repl])
result = rlm.run("Напиши Python код для вычисления fibonacci(20)")
```

## Полное приложение агента

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

# Пользовательские инструменты
@Tool(name="send_email", description="Отправить email")
def send_email(to: str, subject: str, body: str) -> str:
    # Симуляция
    return f"Email отправлен на {to}"

@Tool(name="create_reminder", description="Создать напоминание")
def create_reminder(message: str, when: str) -> str:
    return f"Напоминание установлено: '{message}' на {when}"

def create_assistant():
    """Создаём способного AI-ассистента."""
    
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
    
    system_prompt = """Ты полезный AI-ассистент с доступом к различным инструментам.
    Используй инструменты при необходимости для предоставления точной информации.
    Думай пошагово перед действием.
    Всегда давай чёткие, лаконичные ответы."""
    
    return RLM.from_openai(
        "gpt-4o",
        config=config,
        memory=memory,
        tools=tools,
        system_prompt=system_prompt
    )

def main():
    print("="*50)
    print("🤖 AI Ассистент")
    print("   Команды: 'выход', 'инструменты', 'история'")
    print("="*50)
    
    agent = create_assistant()
    
    while True:
        user_input = input("\n👤 Вы: ").strip()
        
        if not user_input:
            continue
        
        if user_input in ['выход', 'quit']:
            break
        
        if user_input in ['инструменты', 'tools']:
            print("Доступные инструменты:")
            for tool in agent.tools:
                print(f"  - {tool.name}: {tool.description}")
            continue
        
        if user_input in ['история', 'history']:
            for msg in agent.memory.get_recent(5):
                print(f"  {msg}")
            continue
        
        result = agent.run(user_input)
        print(f"\n🤖 Ассистент: {result.answer}")
        
        if result.tool_calls:
            print(f"\n📎 Использованные инструменты: {[t.name for t in result.tool_calls]}")

if __name__ == "__main__":
    main()
```

## Лучшие практики для агентов

!!! tip "Выбор инструментов"
    Предоставляйте чёткие, различающиеся описания инструментов, чтобы помочь агенту выбрать правильный.

!!! tip "Обработка ошибок"
    Инструменты должны возвращать понятные сообщения об ошибках:
    ```python
    @Tool(name="api_call")
    def api_call(endpoint: str) -> str:
        try:
            response = requests.get(endpoint)
            return response.json()
        except Exception as e:
            return f"Ошибка: {str(e)}. Попробуйте другой endpoint."
    ```

!!! tip "Лимиты итераций"
    Устанавливайте разумные ограничения для предотвращения бесконечных циклов:
    ```python
    config = RLMConfig(max_iterations=10)
    ```

!!! warning "Безопасность"
    Всегда используйте песочницу для инструментов выполнения кода:
    ```python
    SecurePythonREPL(sandbox=True, enable_network=False)
    ```

## Следующие шаги

- [Туториал 5: Системы памяти](05-memory.md)
- [Туториал 9: Multi-Agent](09-multiagent.md)
- [Концепция: Агенты](../concepts/agents.md)
