# Туториал 13: Кастомные Callbacks

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> Создавайте кастомные обработчики событий для полного контроля

## Что вы изучите

- Создание кастомных callbacks
- Логирование всех LLM взаимодействий
- Построение streaming UI
- Реализация логики ретраев

## Требования

```bash
pip install rlm-toolkit
```

---

## Часть 1: Базовый Callback

### 1.1 Callback для логирования

```python
from rlm_toolkit import RLM
from rlm_toolkit.callbacks import BaseCallback

class SimpleLogger(BaseCallback):
    def on_llm_start(self, prompt, **kwargs):
        print(f"📤 Отправка промпта ({len(prompt)} символов)")
    
    def on_llm_end(self, response, **kwargs):
        print(f"📥 Получено ({response.usage.total_tokens} токенов)")
    
    def on_error(self, error, **kwargs):
        print(f"❌ Ошибка: {error}")

rlm = RLM.from_openai("gpt-4o", callbacks=[SimpleLogger()])
result = rlm.run("Привет!")
```

**Вывод:**
```
📤 Отправка промпта (7 символов)
📥 Получено (45 токенов)
```

---

## Часть 2: Сборщик метрик

### 2.1 Полный Metrics Callback

```python
from rlm_toolkit.callbacks import BaseCallback
import time
from collections import defaultdict

class MetricsCollector(BaseCallback):
    def __init__(self):
        self.calls = 0
        self.tokens = 0
        self.errors = 0
        self.latencies = []
        self.start_time = None
        self.by_model = defaultdict(int)
    
    def on_llm_start(self, prompt, **kwargs):
        self.start_time = time.time()
        self.calls += 1
    
    def on_llm_end(self, response, **kwargs):
        latency = time.time() - self.start_time
        self.latencies.append(latency)
        self.tokens += response.usage.total_tokens
        self.by_model[kwargs.get("model", "unknown")] += 1
    
    def on_error(self, error, **kwargs):
        self.errors += 1
    
    def summary(self):
        avg_latency = sum(self.latencies) / len(self.latencies) if self.latencies else 0
        return {
            "total_calls": self.calls,
            "total_tokens": self.tokens,
            "errors": self.errors,
            "avg_latency_ms": avg_latency * 1000,
            "by_model": dict(self.by_model)
        }

# Использование
metrics = MetricsCollector()
rlm = RLM.from_openai("gpt-4o", callbacks=[metrics])

for i in range(10):
    rlm.run(f"Вопрос {i}")

print(metrics.summary())
```

---

## Часть 3: Streaming UI

### 3.1 Потоковый вывод токенов

```python
from rlm_toolkit.callbacks import StreamingCallback

def print_token(token):
    print(token, end="", flush=True)

streaming = StreamingCallback(on_token=print_token)
rlm = RLM.from_openai("gpt-4o", callbacks=[streaming])

# Токены появляются по одному
result = rlm.run("Напиши хайку о программировании")
print()  # Новая строка в конце
```

### 3.2 Rich Console UI

```python
from rich.live import Live
from rich.markdown import Markdown

class RichStreamCallback(StreamingCallback):
    def __init__(self):
        self.buffer = ""
        self.live = None
    
    def on_llm_start(self, **kwargs):
        self.buffer = ""
        self.live = Live(Markdown(""), refresh_per_second=10)
        self.live.start()
    
    def on_token(self, token):
        self.buffer += token
        self.live.update(Markdown(self.buffer))
    
    def on_llm_end(self, **kwargs):
        self.live.stop()
```

---

## Часть 4: Обработчик ретраев

### 4.1 Умная логика ретраев

```python
import time
from rlm_toolkit.callbacks import BaseCallback

class RetryHandler(BaseCallback):
    def __init__(self, max_retries=3, backoff=2.0):
        self.max_retries = max_retries
        self.backoff = backoff
        self.retry_count = 0
    
    def on_retry(self, attempt, max_attempts, error, **kwargs):
        wait_time = self.backoff ** attempt
        print(f"⚠️ Ретрай {attempt}/{max_attempts} через {wait_time}s: {error}")
        time.sleep(wait_time)
        self.retry_count += 1
    
    def on_error(self, error, **kwargs):
        print(f"❌ Финальная ошибка после {self.retry_count} ретраев: {error}")

rlm = RLM.from_openai("gpt-4o", callbacks=[RetryHandler()])
```

---

## Часть 5: Файловый логгер

### 5.1 JSONL лог

```python
import json
from datetime import datetime
from rlm_toolkit.callbacks import BaseCallback

class JSONLLogger(BaseCallback):
    def __init__(self, path="rlm_logs.jsonl"):
        self.path = path
        self.file = open(path, "a")
    
    def _log(self, event_type, data):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            **data
        }
        self.file.write(json.dumps(entry) + "\n")
        self.file.flush()
    
    def on_llm_start(self, prompt, **kwargs):
        self._log("llm_start", {"prompt": prompt[:200]})
    
    def on_llm_end(self, response, **kwargs):
        self._log("llm_end", {
            "tokens": response.usage.total_tokens,
            "response": response.content[:200]
        })
    
    def on_tool_start(self, tool_name, tool_input, **kwargs):
        self._log("tool_start", {"tool": tool_name, "input": str(tool_input)[:100]})
    
    def on_error(self, error, **kwargs):
        self._log("error", {"error": str(error)})
    
    def close(self):
        self.file.close()

logger = JSONLLogger("session.jsonl")
rlm = RLM.from_openai("gpt-4o", callbacks=[logger])
```

---

## Часть 6: Комбинирование Callbacks

```python
from rlm_toolkit.callbacks import ConsoleCallback

callbacks = [
    SimpleLogger(),
    MetricsCollector(),
    JSONLLogger("full_log.jsonl")
]

rlm = RLM.from_openai("gpt-4o", callbacks=callbacks)
```

---

## Результаты

Теперь у вас полная видимость и контроль:
- ✅ Real-time логирование
- ✅ Сбор метрик
- ✅ Streaming UI
- ✅ Автоматические ретраи
- ✅ Персистентные логи

---

## Следующие шаги

- [Концепция: Callbacks](../concepts/callbacks.md)
- [Туториал: Observability](12-observability.md)
- [Концепция: Agents](../concepts/agents.md)
