# How-to: Streaming

Recipes for streaming LLM responses.

## Basic Streaming

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")

for chunk in rlm.stream("Tell me a story"):
    print(chunk, end="", flush=True)
```

## Async Streaming

```python
import asyncio
from rlm_toolkit import RLM

async def stream_response():
    rlm = RLM.from_openai("gpt-4o")
    
    async for chunk in rlm.astream("Tell me a story"):
        print(chunk, end="", flush=True)

asyncio.run(stream_response())
```

## Streaming with Callback

```python
from rlm_toolkit import RLM
from rlm_toolkit.callbacks import StreamingCallback

class MyStreamer(StreamingCallback):
    def on_llm_new_token(self, token: str, **kwargs):
        print(token, end="", flush=True)

rlm = RLM.from_openai("gpt-4o", callbacks=[MyStreamer()])
rlm.run("Tell me a story")
```

## Agent Streaming

```python
from rlm_toolkit.agents import ReActAgent

agent = ReActAgent.from_openai("gpt-4o", tools=[...])

for event in agent.stream("Research Python"):
    if event.type == "thought":
        print(f"\n[Thinking] {event.content}")
    elif event.type == "action":
        print(f"\n[Action] {event.tool_name}({event.input})")
    elif event.type == "observation":
        print(f"\n[Result] {event.content[:100]}...")
    elif event.type == "token":
        print(event.content, end="", flush=True)
    elif event.type == "final":
        print(f"\n[Answer] {event.content}")
```

## Streaming to File

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")

with open("output.txt", "w") as f:
    for chunk in rlm.stream("Write an essay"):
        f.write(chunk)
        print(chunk, end="", flush=True)
```

## Streaming to WebSocket

```python
import asyncio
from fastapi import FastAPI, WebSocket
from rlm_toolkit import RLM

app = FastAPI()
rlm = RLM.from_openai("gpt-4o")

@app.websocket("/chat")
async def chat(websocket: WebSocket):
    await websocket.accept()
    message = await websocket.receive_text()
    
    async for chunk in rlm.astream(message):
        await websocket.send_text(chunk)
```

## Streaming with SSE (Server-Sent Events)

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from rlm_toolkit import RLM

app = FastAPI()
rlm = RLM.from_openai("gpt-4o")

@app.get("/stream")
async def stream(query: str):
    async def generate():
        async for chunk in rlm.astream(query):
            yield f"data: {chunk}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )
```

## Collect Stream into String

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")

# Collect while printing
chunks = []
for chunk in rlm.stream("Hello"):
    print(chunk, end="", flush=True)
    chunks.append(chunk)

full_response = "".join(chunks)
```

## Related

- [How-to: Callbacks](./callbacks.md)
- [How-to: Providers](./providers.md)
