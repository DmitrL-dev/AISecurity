# How-to: Streaming

Рецепты потоковой передачи ответов LLM.

## Базовый streaming

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")

for chunk in rlm.stream("Расскажи историю"):
    print(chunk, end="", flush=True)
```

## Async streaming

```python
import asyncio
from rlm_toolkit import RLM

async def stream_response():
    rlm = RLM.from_openai("gpt-4o")
    
    async for chunk in rlm.astream("Расскажи историю"):
        print(chunk, end="", flush=True)

asyncio.run(stream_response())
```

## Streaming с callback

```python
from rlm_toolkit import RLM
from rlm_toolkit.callbacks import StreamingCallback

class MyStreamer(StreamingCallback):
    def on_llm_new_token(self, token: str, **kwargs):
        print(token, end="", flush=True)

rlm = RLM.from_openai("gpt-4o", callbacks=[MyStreamer()])
rlm.run("Расскажи историю")
```

## Streaming агента

```python
from rlm_toolkit.agents import ReActAgent

agent = ReActAgent.from_openai("gpt-4o", tools=[...])

for event in agent.stream("Исследуй Python"):
    if event.type == "thought":
        print(f"\n[Думает] {event.content}")
    elif event.type == "action":
        print(f"\n[Действие] {event.tool_name}({event.input})")
    elif event.type == "observation":
        print(f"\n[Результат] {event.content[:100]}...")
    elif event.type == "token":
        print(event.content, end="", flush=True)
    elif event.type == "final":
        print(f"\n[Ответ] {event.content}")
```

## Streaming в файл

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")

with open("output.txt", "w") as f:
    for chunk in rlm.stream("Напиши эссе"):
        f.write(chunk)
        print(chunk, end="", flush=True)
```

## Streaming в WebSocket

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

## Streaming с SSE (Server-Sent Events)

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

## Сбор stream в строку

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")

# Собираем во время вывода
chunks = []
for chunk in rlm.stream("Привет"):
    print(chunk, end="", flush=True)
    chunks.append(chunk)

full_response = "".join(chunks)
```

## Связанное

- [How-to: Callbacks](./callbacks.md)
- [How-to: Провайдеры](./providers.md)
