# How-to: Callbacks и наблюдаемость

Рецепты мониторинга и отладки RLM приложений.

## Базовые callbacks

```python
from rlm_toolkit import RLM
from rlm_toolkit.callbacks import ConsoleCallback

callback = ConsoleCallback(verbose=True)
rlm = RLM.from_openai("gpt-4o", callbacks=[callback])

response = rlm.run("Привет")
# [RLM] Prompt: Привет
# [RLM] Response: Привет!
# [RLM] Tokens: 15 (prompt) + 5 (response)
```

## Интеграция Langfuse

```python
from rlm_toolkit.callbacks import LangfuseCallback

callback = LangfuseCallback(
    public_key="your-public-key",
    secret_key="your-secret-key",
    host="https://cloud.langfuse.com"
)

rlm = RLM.from_openai("gpt-4o", callbacks=[callback])
```

## Интеграция Phoenix (Arize)

```python
from rlm_toolkit.callbacks import PhoenixCallback

callback = PhoenixCallback(
    project_name="my-project",
    endpoint="http://localhost:6006"
)

rlm = RLM.from_openai("gpt-4o", callbacks=[callback])
```

## OpenTelemetry

```python
from rlm_toolkit.callbacks import OpenTelemetryCallback

callback = OpenTelemetryCallback(
    service_name="my-rlm-app",
    endpoint="http://localhost:4317"
)
```

## Подсчёт токенов

```python
from rlm_toolkit.callbacks import TokenCounterCallback

counter = TokenCounterCallback()
rlm = RLM.from_openai("gpt-4o", callbacks=[counter])

rlm.run("Привет")
rlm.run("Мир")

print(f"Всего токенов: {counter.total_tokens}")
print(f"Prompt токенов: {counter.prompt_tokens}")
print(f"Completion токенов: {counter.completion_tokens}")
```

## Отслеживание стоимости

```python
from rlm_toolkit.callbacks import CostCallback

cost_tracker = CostCallback()
rlm = RLM.from_openai("gpt-4o", callbacks=[cost_tracker])

rlm.run("Долгий разговор...")

print(f"Общая стоимость: ${cost_tracker.total_cost:.4f}")
```

## Мониторинг латентности

```python
from rlm_toolkit.callbacks import LatencyCallback

latency = LatencyCallback()
rlm = RLM.from_openai("gpt-4o", callbacks=[latency])

rlm.run("Привет")

print(f"Последняя латентность: {latency.last_latency:.2f}s")
print(f"Средняя латентность: {latency.avg_latency:.2f}s")
```

## Пользовательский callback

```python
from rlm_toolkit.callbacks import BaseCallback

class MyCallback(BaseCallback):
    def on_llm_start(self, prompt: str, **kwargs):
        print(f"Запуск LLM с: {prompt[:50]}...")
    
    def on_llm_end(self, response: str, **kwargs):
        print(f"LLM ответил: {response[:50]}...")
    
    def on_llm_error(self, error: Exception, **kwargs):
        print(f"Ошибка: {error}")
    
    def on_tool_start(self, tool_name: str, **kwargs):
        print(f"Использование инструмента: {tool_name}")
    
    def on_tool_end(self, output: str, **kwargs):
        print(f"Вывод инструмента: {output[:50]}...")
```

## Несколько callbacks

```python
from rlm_toolkit.callbacks import (
    ConsoleCallback,
    TokenCounterCallback,
    LangfuseCallback
)

callbacks = [
    ConsoleCallback(verbose=True),
    TokenCounterCallback(),
    LangfuseCallback(...)
]

rlm = RLM.from_openai("gpt-4o", callbacks=callbacks)
```

## Agent-специфичные callbacks

```python
from rlm_toolkit.callbacks import AgentCallback

class AgentLogger(AgentCallback):
    def on_agent_action(self, action: str, tool: str, **kwargs):
        print(f"Агент решил: {action} используя {tool}")
    
    def on_agent_finish(self, output: str, **kwargs):
        print(f"Агент завершил: {output}")
```

## Связанное

- [How-to: Streaming](./streaming.md)
- [Туториал: Первое приложение](../tutorials/01-first-app.md)
