# Callbacks

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **Event hooks** для мониторинга и кастомизации

## Обзор

Callbacks позволяют подключаться к событиям жизненного цикла RLM:
- LLM запросы/ответы
- Tool вызовы
- Операции памяти
- Ошибки и ретраи

## Быстрый старт

```python
from rlm_toolkit import RLM
from rlm_toolkit.callbacks import BaseCallback

class LoggingCallback(BaseCallback):
    def on_llm_start(self, prompt, **kwargs):
        print(f"📤 Отправка: {prompt[:50]}...")
    
    def on_llm_end(self, response, **kwargs):
        print(f"📥 Получено: {response.content[:50]}...")
    
    def on_error(self, error, **kwargs):
        print(f"❌ Ошибка: {error}")

rlm = RLM.from_openai("gpt-4o", callbacks=[LoggingCallback()])
result = rlm.run("Привет!")
```

## События Callback

| Событие | Когда срабатывает |
|---------|-------------------|
| `on_llm_start` | Перед вызовом LLM |
| `on_llm_end` | После ответа LLM |
| `on_tool_start` | Перед выполнением tool |
| `on_tool_end` | После выполнения tool |
| `on_memory_store` | При сохранении в память |
| `on_memory_recall` | При извлечении из памяти |
| `on_retry` | При попытке ретрая |
| `on_error` | При ошибке |

## Встроенные Callbacks

### ConsoleCallback

```python
from rlm_toolkit.callbacks import ConsoleCallback

callback = ConsoleCallback(
    verbose=True,
    show_tokens=True,
    show_cost=True
)

rlm = RLM.from_openai("gpt-4o", callbacks=[callback])
```

### StreamingCallback

```python
from rlm_toolkit.callbacks import StreamingCallback

def print_token(token):
    print(token, end="", flush=True)

callback = StreamingCallback(on_token=print_token)
rlm = RLM.from_openai("gpt-4o", callbacks=[callback])
```

### MetricsCallback

```python
from rlm_toolkit.callbacks import MetricsCallback

callback = MetricsCallback()
rlm = RLM.from_openai("gpt-4o", callbacks=[callback])

# Выполняем запросы
rlm.run("Запрос 1")
rlm.run("Запрос 2")

# Получаем метрики
metrics = callback.get_metrics()
print(f"Всего вызовов: {metrics['total_calls']}")
print(f"Всего токенов: {metrics['total_tokens']}")
print(f"Средняя латентность: {metrics['avg_latency_ms']}ms")
```

### FileLogCallback

```python
from rlm_toolkit.callbacks import FileLogCallback

callback = FileLogCallback(
    log_path="./logs/rlm.jsonl",
    include_prompts=True,
    include_responses=True
)

rlm = RLM.from_openai("gpt-4o", callbacks=[callback])
```

## Кастомные Callbacks

### Полный пример

```python
from rlm_toolkit.callbacks import BaseCallback
import time

class DetailedCallback(BaseCallback):
    def __init__(self):
        self.call_count = 0
        self.total_tokens = 0
        self.errors = []
        self.start_time = None
    
    def on_llm_start(self, prompt, **kwargs):
        self.start_time = time.time()
        self.call_count += 1
        print(f"[{self.call_count}] Запуск LLM вызова...")
    
    def on_llm_end(self, response, **kwargs):
        duration = time.time() - self.start_time
        tokens = response.usage.total_tokens
        self.total_tokens += tokens
        print(f"[{self.call_count}] Завершено за {duration:.2f}s ({tokens} токенов)")
    
    def on_tool_start(self, tool_name, tool_input, **kwargs):
        print(f"🔧 Tool: {tool_name}({tool_input})")
    
    def on_tool_end(self, tool_name, tool_output, **kwargs):
        print(f"✅ Результат tool: {tool_output[:100]}...")
    
    def on_memory_store(self, content, **kwargs):
        print(f"💾 Сохранено: {content[:50]}...")
    
    def on_memory_recall(self, query, results, **kwargs):
        print(f"🔍 Извлечено {len(results)} элементов для: {query}")
    
    def on_error(self, error, **kwargs):
        self.errors.append(str(error))
        print(f"❌ Ошибка: {error}")
    
    def on_retry(self, attempt, max_attempts, error, **kwargs):
        print(f"🔄 Ретрай {attempt}/{max_attempts}: {error}")
    
    def summary(self):
        return {
            "calls": self.call_count,
            "tokens": self.total_tokens,
            "errors": len(self.errors)
        }
```

### Async Callback

```python
from rlm_toolkit.callbacks import AsyncBaseCallback

class AsyncLoggingCallback(AsyncBaseCallback):
    async def on_llm_start(self, prompt, **kwargs):
        await self.log_async(f"Запуск: {prompt[:50]}...")
    
    async def on_llm_end(self, response, **kwargs):
        await self.log_async(f"Завершено: {response.content[:50]}...")
    
    async def log_async(self, message):
        # Асинхронный лог во внешний сервис
        async with aiohttp.ClientSession() as session:
            await session.post(
                "https://logging-service.com/log",
                json={"message": message}
            )
```

## Комбинирование Callbacks

```python
from rlm_toolkit.callbacks import (
    ConsoleCallback,
    MetricsCallback,
    FileLogCallback
)

callbacks = [
    ConsoleCallback(verbose=True),
    MetricsCallback(),
    FileLogCallback(log_path="./session.jsonl")
]

rlm = RLM.from_openai("gpt-4o", callbacks=callbacks)
```

## Связанное

- [Observability](observability.md)
- [Agents](agents.md)
- [Туториал: Первое приложение](../tutorials/01-first-app.md)
