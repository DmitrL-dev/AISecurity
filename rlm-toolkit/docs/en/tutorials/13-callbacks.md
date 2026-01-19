# Tutorial 13: Custom Callbacks

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> Build custom event handlers for complete control

## What You'll Learn

- Create custom callbacks
- Log all LLM interactions
- Build a streaming UI
- Implement retry logic

## Prerequisites

```bash
pip install rlm-toolkit
```

---

## Part 1: Basic Callback

### 1.1 Logging Callback

```python
from rlm_toolkit import RLM
from rlm_toolkit.callbacks import BaseCallback

class SimpleLogger(BaseCallback):
    def on_llm_start(self, prompt, **kwargs):
        print(f"📤 Sending prompt ({len(prompt)} chars)")
    
    def on_llm_end(self, response, **kwargs):
        print(f"📥 Received ({response.usage.total_tokens} tokens)")
    
    def on_error(self, error, **kwargs):
        print(f"❌ Error: {error}")

rlm = RLM.from_openai("gpt-4o", callbacks=[SimpleLogger()])
result = rlm.run("Hello!")
```

**Output:**
```
📤 Sending prompt (6 chars)
📥 Received (45 tokens)
```

---

## Part 2: Metrics Collector

### 2.1 Full Metrics Callback

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

# Use it
metrics = MetricsCollector()
rlm = RLM.from_openai("gpt-4o", callbacks=[metrics])

for i in range(10):
    rlm.run(f"Question {i}")

print(metrics.summary())
```

---

## Part 3: Streaming UI

### 3.1 Token-by-Token Output

```python
from rlm_toolkit.callbacks import StreamingCallback

def print_token(token):
    print(token, end="", flush=True)

streaming = StreamingCallback(on_token=print_token)
rlm = RLM.from_openai("gpt-4o", callbacks=[streaming])

# Tokens appear one by one
result = rlm.run("Write a haiku about coding")
print()  # Newline at end
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

## Part 4: Retry Handler

### 4.1 Smart Retry Logic

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
        print(f"⚠️ Retry {attempt}/{max_attempts} in {wait_time}s: {error}")
        time.sleep(wait_time)
        self.retry_count += 1
    
    def on_error(self, error, **kwargs):
        print(f"❌ Final error after {self.retry_count} retries: {error}")

rlm = RLM.from_openai("gpt-4o", callbacks=[RetryHandler()])
```

---

## Part 5: File Logger

### 5.1 JSONL Log

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

## Part 6: Combining Callbacks

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

## Results

Now you have complete visibility and control:
- ✅ Real-time logging
- ✅ Metrics collection
- ✅ Streaming UI
- ✅ Automatic retries
- ✅ Persistent logs

---

## Next Steps

- [Concept: Callbacks](../concepts/callbacks.md)
- [Tutorial: Observability](12-observability.md)
- [Concept: Agents](../concepts/agents.md)
