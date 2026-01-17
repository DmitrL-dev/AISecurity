# How-to: Callbacks and Observability

Recipes for monitoring and debugging RLM applications.

## Basic Callbacks

```python
from rlm_toolkit import RLM
from rlm_toolkit.callbacks import ConsoleCallback

callback = ConsoleCallback(verbose=True)
rlm = RLM.from_openai("gpt-4o", callbacks=[callback])

response = rlm.run("Hello")
# [RLM] Prompt: Hello
# [RLM] Response: Hi there!
# [RLM] Tokens: 15 (prompt) + 5 (response)
```

## Langfuse Integration

```python
from rlm_toolkit.callbacks import LangfuseCallback

callback = LangfuseCallback(
    public_key="your-public-key",
    secret_key="your-secret-key",
    host="https://cloud.langfuse.com"
)

rlm = RLM.from_openai("gpt-4o", callbacks=[callback])
```

## Phoenix (Arize) Integration

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

## Token Counting

```python
from rlm_toolkit.callbacks import TokenCounterCallback

counter = TokenCounterCallback()
rlm = RLM.from_openai("gpt-4o", callbacks=[counter])

rlm.run("Hello")
rlm.run("World")

print(f"Total tokens: {counter.total_tokens}")
print(f"Prompt tokens: {counter.prompt_tokens}")
print(f"Completion tokens: {counter.completion_tokens}")
```

## Cost Tracking

```python
from rlm_toolkit.callbacks import CostCallback

cost_tracker = CostCallback()
rlm = RLM.from_openai("gpt-4o", callbacks=[cost_tracker])

rlm.run("Long conversation...")

print(f"Total cost: ${cost_tracker.total_cost:.4f}")
```

## Latency Monitoring

```python
from rlm_toolkit.callbacks import LatencyCallback

latency = LatencyCallback()
rlm = RLM.from_openai("gpt-4o", callbacks=[latency])

rlm.run("Hello")

print(f"Last latency: {latency.last_latency:.2f}s")
print(f"Avg latency: {latency.avg_latency:.2f}s")
```

## Custom Callback

```python
from rlm_toolkit.callbacks import BaseCallback

class MyCallback(BaseCallback):
    def on_llm_start(self, prompt: str, **kwargs):
        print(f"Starting LLM with: {prompt[:50]}...")
    
    def on_llm_end(self, response: str, **kwargs):
        print(f"LLM responded: {response[:50]}...")
    
    def on_llm_error(self, error: Exception, **kwargs):
        print(f"Error: {error}")
    
    def on_tool_start(self, tool_name: str, **kwargs):
        print(f"Using tool: {tool_name}")
    
    def on_tool_end(self, output: str, **kwargs):
        print(f"Tool output: {output[:50]}...")
```

## Multiple Callbacks

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

## Agent-Specific Callbacks

```python
from rlm_toolkit.callbacks import AgentCallback

class AgentLogger(AgentCallback):
    def on_agent_action(self, action: str, tool: str, **kwargs):
        print(f"Agent decided: {action} using {tool}")
    
    def on_agent_finish(self, output: str, **kwargs):
        print(f"Agent finished: {output}")
```

## Related

- [How-to: Streaming](./streaming.md)
- [Tutorial: First App](../tutorials/01-first-app.md)
