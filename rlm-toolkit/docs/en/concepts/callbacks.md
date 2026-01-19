# Callbacks

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **Event hooks** for monitoring and customization

## Overview

Callbacks let you hook into RLM lifecycle events:
- LLM requests/responses
- Tool calls
- Memory operations
- Errors and retries

## Quick Start

```python
from rlm_toolkit import RLM
from rlm_toolkit.callbacks import BaseCallback

class LoggingCallback(BaseCallback):
    def on_llm_start(self, prompt, **kwargs):
        print(f"📤 Sending: {prompt[:50]}...")
    
    def on_llm_end(self, response, **kwargs):
        print(f"📥 Received: {response.content[:50]}...")
    
    def on_error(self, error, **kwargs):
        print(f"❌ Error: {error}")

rlm = RLM.from_openai("gpt-4o", callbacks=[LoggingCallback()])
result = rlm.run("Hello!")
```

## Callback Events

| Event | When Fired |
|-------|------------|
| `on_llm_start` | Before LLM call |
| `on_llm_end` | After LLM response |
| `on_tool_start` | Before tool execution |
| `on_tool_end` | After tool execution |
| `on_memory_store` | When storing to memory |
| `on_memory_recall` | When recalling from memory |
| `on_retry` | On retry attempt |
| `on_error` | On error |

## Built-in Callbacks

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

# Run some queries
rlm.run("Query 1")
rlm.run("Query 2")

# Get metrics
metrics = callback.get_metrics()
print(f"Total calls: {metrics['total_calls']}")
print(f"Total tokens: {metrics['total_tokens']}")
print(f"Avg latency: {metrics['avg_latency_ms']}ms")
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

## Custom Callbacks

### Full Example

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
        print(f"[{self.call_count}] Starting LLM call...")
    
    def on_llm_end(self, response, **kwargs):
        duration = time.time() - self.start_time
        tokens = response.usage.total_tokens
        self.total_tokens += tokens
        print(f"[{self.call_count}] Completed in {duration:.2f}s ({tokens} tokens)")
    
    def on_tool_start(self, tool_name, tool_input, **kwargs):
        print(f"🔧 Tool: {tool_name}({tool_input})")
    
    def on_tool_end(self, tool_name, tool_output, **kwargs):
        print(f"✅ Tool result: {tool_output[:100]}...")
    
    def on_memory_store(self, content, **kwargs):
        print(f"💾 Stored: {content[:50]}...")
    
    def on_memory_recall(self, query, results, **kwargs):
        print(f"🔍 Recalled {len(results)} items for: {query}")
    
    def on_error(self, error, **kwargs):
        self.errors.append(str(error))
        print(f"❌ Error: {error}")
    
    def on_retry(self, attempt, max_attempts, error, **kwargs):
        print(f"🔄 Retry {attempt}/{max_attempts}: {error}")
    
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
        await self.log_async(f"Starting: {prompt[:50]}...")
    
    async def on_llm_end(self, response, **kwargs):
        await self.log_async(f"Completed: {response.content[:50]}...")
    
    async def log_async(self, message):
        # Log to external service asynchronously
        async with aiohttp.ClientSession() as session:
            await session.post(
                "https://logging-service.com/log",
                json={"message": message}
            )
```

## Combining Callbacks

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

## Related

- [Observability](observability.md)
- [Agents](agents.md)
- [Tutorial: First App](../tutorials/01-first-app.md)
