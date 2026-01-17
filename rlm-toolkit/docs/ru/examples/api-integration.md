# Примеры интеграции API

Полные примеры создания API с RLM.

## REST API с FastAPI

```python
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rlm_toolkit import RLM
from rlm_toolkit.memory import SessionMemory
import uuid
from typing import Optional, List

app = FastAPI(
    title="RLM API",
    description="Production-ready LLM API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Управление сессиями
sessions = {}

def get_rlm(session_id: str) -> RLM:
    if session_id not in sessions:
        sessions[session_id] = RLM.from_openai(
            "gpt-4o",
            memory=SessionMemory(session_id=session_id)
        )
    return sessions[session_id]

# Модели Request/Response
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = 0.7

class ChatResponse(BaseModel):
    response: str
    session_id: str

class Message(BaseModel):
    role: str
    content: str

class MultiTurnRequest(BaseModel):
    messages: List[Message]
    system_prompt: Optional[str] = None

# Эндпоинты
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    rlm = get_rlm(session_id)
    
    if request.system_prompt:
        rlm.set_system_prompt(request.system_prompt)
    
    response = rlm.run(request.message)
    return ChatResponse(response=response, session_id=session_id)

@app.post("/complete")
async def complete(request: MultiTurnRequest):
    rlm = RLM.from_openai("gpt-4o")
    if request.system_prompt:
        rlm.set_system_prompt(request.system_prompt)
    
    for msg in request.messages[:-1]:
        if msg.role == "user":
            rlm.memory.add_user_message(msg.content)
        else:
            rlm.memory.add_assistant_message(msg.content)
    
    response = rlm.run(request.messages[-1].content)
    return {"response": response}

@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    if session_id in sessions:
        del sessions[session_id]
    return {"status": "deleted"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

## Streaming API

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from rlm_toolkit import RLM
import json

app = FastAPI()
rlm = RLM.from_openai("gpt-4o")

@app.get("/stream")
async def stream(query: str):
    async def generate():
        async for chunk in rlm.astream(query):
            data = json.dumps({"content": chunk})
            yield f"data: {data}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"}
    )

# Использование на клиенте
"""
const eventSource = new EventSource('/stream?query=Привет');
eventSource.onmessage = (event) => {
    if (event.data === '[DONE]') {
        eventSource.close();
        return;
    }
    const data = JSON.parse(event.data);
    console.log(data.content);
};
"""
```

## WebSocket API

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from rlm_toolkit import RLM
from rlm_toolkit.memory import SessionMemory
import json

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.connections: dict = {}
        
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.connections[session_id] = {
            "ws": websocket,
            "rlm": RLM.from_openai("gpt-4o", memory=SessionMemory(session_id))
        }
        
    def disconnect(self, session_id: str):
        if session_id in self.connections:
            del self.connections[session_id]
            
    async def send_message(self, session_id: str, message: dict):
        ws = self.connections[session_id]["ws"]
        await ws.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            request = json.loads(data)
            
            rlm = manager.connections[session_id]["rlm"]
            
            if request.get("stream", False):
                async for chunk in rlm.astream(request["message"]):
                    await manager.send_message(session_id, {
                        "type": "chunk",
                        "content": chunk
                    })
                await manager.send_message(session_id, {"type": "done"})
            else:
                response = rlm.run(request["message"])
                await manager.send_message(session_id, {
                    "type": "response",
                    "content": response
                })
    except WebSocketDisconnect:
        manager.disconnect(session_id)
```

## Rate Limited API

```python
from fastapi import FastAPI, HTTPException, Depends, Request
from rlm_toolkit import RLM
import time
from collections import defaultdict

app = FastAPI()
rlm = RLM.from_openai("gpt-4o")

# Простой rate limiter
class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)
        
    def check(self, client_ip: str) -> bool:
        now = time.time()
        minute_ago = now - 60
        
        self.requests[client_ip] = [
            r for r in self.requests[client_ip] if r > minute_ago
        ]
        
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            return False
            
        self.requests[client_ip].append(now)
        return True

rate_limiter = RateLimiter(requests_per_minute=60)

def check_rate_limit(request: Request):
    client_ip = request.client.host
    if not rate_limiter.check(client_ip):
        raise HTTPException(status_code=429, detail="Лимит запросов превышен")
    return True

@app.post("/chat")
async def chat(message: str, _: bool = Depends(check_rate_limit)):
    response = rlm.run(message)
    return {"response": response}
```

## Authenticated API

```python
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from rlm_toolkit import RLM
import jwt
from datetime import datetime, timedelta

app = FastAPI()
security = HTTPBearer()
SECRET_KEY = "your-secret-key"

# Управление токенами
def create_token(user_id: str) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(
            credentials.credentials, 
            SECRET_KEY, 
            algorithms=["HS256"]
        )
        return payload["user_id"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Токен истёк")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Невалидный токен")

# RLM инстансы по пользователям
user_rlms = {}

def get_user_rlm(user_id: str = Depends(verify_token)) -> RLM:
    if user_id not in user_rlms:
        user_rlms[user_id] = RLM.from_openai("gpt-4o")
    return user_rlms[user_id]

@app.post("/login")
async def login(username: str, password: str):
    if username and password:  # Упрощённо
        token = create_token(username)
        return {"access_token": token}
    raise HTTPException(status_code=401, detail="Неверные данные")

@app.post("/chat")
async def chat(message: str, rlm: RLM = Depends(get_user_rlm)):
    response = rlm.run(message)
    return {"response": response}
```

## RAG API

```python
from fastapi import FastAPI, UploadFile, File, HTTPException
from rlm_toolkit import RLM
from rlm_toolkit.loaders import PDFLoader
from rlm_toolkit.splitters import RecursiveTextSplitter
from rlm_toolkit.embeddings import OpenAIEmbeddings
from rlm_toolkit.vectorstores import ChromaVectorStore
import tempfile
import os

app = FastAPI()

# Глобальные RAG компоненты
vectorstore = None
rlm = RLM.from_openai("gpt-4o")

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    global vectorstore
    
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Поддерживаются только PDF файлы")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
        f.write(await file.read())
        temp_path = f.name
    
    try:
        docs = PDFLoader(temp_path).load()
        chunks = RecursiveTextSplitter(chunk_size=1000).split_documents(docs)
        
        embeddings = OpenAIEmbeddings()
        
        if vectorstore is None:
            vectorstore = ChromaVectorStore.from_documents(chunks, embeddings)
        else:
            vectorstore.add_documents(chunks)
            
        rlm.set_retriever(vectorstore.as_retriever(k=5))
        
        return {"status": "uploaded", "chunks": len(chunks)}
    finally:
        os.unlink(temp_path)

@app.post("/query")
async def query(question: str):
    if vectorstore is None:
        raise HTTPException(400, "Документы не загружены")
    
    response = rlm.run(question)
    return {"answer": response}

@app.delete("/documents")
async def clear_documents():
    global vectorstore
    vectorstore = None
    return {"status": "cleared"}
```

## Batch Processing API

```python
from fastapi import FastAPI, BackgroundTasks
from rlm_toolkit import RLM
from pydantic import BaseModel
from typing import List
import uuid
import asyncio

app = FastAPI()
rlm = RLM.from_openai("gpt-4o")

# Хранение задач
jobs = {}

class BatchRequest(BaseModel):
    prompts: List[str]

class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    total: int
    results: List[str] = []

async def process_batch(job_id: str, prompts: List[str]):
    jobs[job_id]["status"] = "processing"
    
    for i, prompt in enumerate(prompts):
        response = rlm.run(prompt)
        jobs[job_id]["results"].append(response)
        jobs[job_id]["progress"] = i + 1
        await asyncio.sleep(0.1)
        
    jobs[job_id]["status"] = "completed"

@app.post("/batch")
async def create_batch(request: BatchRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    
    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "total": len(request.prompts),
        "results": []
    }
    
    background_tasks.add_task(process_batch, job_id, request.prompts)
    
    return {"job_id": job_id}

@app.get("/batch/{job_id}", response_model=JobStatus)
async def get_batch_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Задача не найдена")
    
    job = jobs[job_id]
    return JobStatus(
        job_id=job_id,
        **job
    )
```

## Multi-Model Router

```python
from fastapi import FastAPI
from rlm_toolkit import RLM
from pydantic import BaseModel
from enum import Enum

app = FastAPI()

class ModelType(str, Enum):
    GPT4 = "gpt-4o"
    GPT4_MINI = "gpt-4o-mini"
    CLAUDE = "claude-3-sonnet"
    GEMINI = "gemini-pro"

# Предварительная инициализация моделей
models = {
    ModelType.GPT4: RLM.from_openai("gpt-4o"),
    ModelType.GPT4_MINI: RLM.from_openai("gpt-4o-mini"),
    ModelType.CLAUDE: RLM.from_anthropic("claude-3-sonnet"),
    ModelType.GEMINI: RLM.from_google("gemini-pro")
}

class ChatRequest(BaseModel):
    message: str
    model: ModelType = ModelType.GPT4

@app.post("/chat")
async def chat(request: ChatRequest):
    rlm = models[request.model]
    response = rlm.run(request.message)
    return {"response": response, "model": request.model}

@app.post("/compare")
async def compare(message: str):
    """Сравнение ответов всех моделей"""
    results = {}
    for model_type, rlm in models.items():
        results[model_type] = rlm.run(message)
    return results
```

## Связанное

- [Галерея примеров](./index.md)
- [How-to: Развёртывание](../how-to/deployment.md)
- [How-to: Streaming](../how-to/streaming.md)
