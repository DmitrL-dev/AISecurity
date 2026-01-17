# Examples Gallery

Practical, ready-to-use examples for every RLM-Toolkit use case.

## Quick Links

| Category | Examples |
|----------|----------|
| [Basic](#basic) | Hello World, Chat, Streaming |
| [RAG](#rag) | PDF Q&A, Web Scraper, Hybrid Search |
| [Agents](#agents) | Research Agent, Code Assistant, Data Analyst |
| [Memory](#memory) | Persistent Chat, H-MEM, Session Manager |
| [Advanced](#advanced) | InfiniRetri, Self-Evolving, Multi-Agent |
| [Production](#production) | FastAPI, Docker, Kubernetes |
| [Integrations](#integrations) | Slack Bot, Discord, Telegram |

---

## Basic

### Hello World

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")
print(rlm.run("Hello, world!"))
```

### Simple Chat

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import BufferMemory

rlm = RLM.from_openai("gpt-4o", memory=BufferMemory())

while True:
    user_input = input("You: ")
    if user_input.lower() == "quit":
        break
    response = rlm.run(user_input)
    print(f"AI: {response}")
```

### Streaming Response

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")

for chunk in rlm.stream("Tell me a story about a robot"):
    print(chunk, end="", flush=True)
```

### JSON Output

```python
from rlm_toolkit import RLM, RLMConfig

config = RLMConfig(json_mode=True)
rlm = RLM.from_openai("gpt-4o", config=config)

result = rlm.run("""
Extract information about this person:
"John Smith, 35, works at Google as a Senior Engineer"

Return as: {"name": str, "age": int, "company": str, "role": str}
""")
print(result)
```

### Structured Output (Pydantic)

```python
from pydantic import BaseModel
from rlm_toolkit import RLM

class Product(BaseModel):
    name: str
    price: float
    in_stock: bool

rlm = RLM.from_openai("gpt-4o")
product = rlm.run_structured(
    "iPhone 15 Pro, $999, available",
    output_schema=Product
)
print(f"{product.name}: ${product.price}")
```

### Multiple Providers

```python
from rlm_toolkit import RLM

# OpenAI
gpt = RLM.from_openai("gpt-4o")

# Anthropic
claude = RLM.from_anthropic("claude-3-sonnet")

# Google
gemini = RLM.from_google("gemini-pro")

# Local (Ollama)
llama = RLM.from_ollama("llama3")

# Compare outputs
query = "Explain quantum computing in one sentence"
print(f"GPT: {gpt.run(query)}")
print(f"Claude: {claude.run(query)}")
print(f"Gemini: {gemini.run(query)}")
print(f"Llama: {llama.run(query)}")
```

### Image Analysis (Vision)

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")

result = rlm.run(
    "What's in this image? Describe in detail.",
    images=["./photo.jpg"]
)
print(result)
```

### Translation

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")
rlm.set_system_prompt("You are a translator. Translate to the requested language.")

text = "Hello, how are you today?"
print(rlm.run(f"Translate to Russian: {text}"))
print(rlm.run(f"Translate to Japanese: {text}"))
print(rlm.run(f"Translate to Spanish: {text}"))
```

### Code Generation

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")
rlm.set_system_prompt("""
You are a Python expert. Generate clean, documented code.
Include type hints and docstrings.
""")

code = rlm.run("Write a function to find all prime numbers up to n")
print(code)
```

### Summarization

```python
from rlm_toolkit import RLM
from rlm_toolkit.loaders import WebPageLoader

rlm = RLM.from_openai("gpt-4o")

# Load article
docs = WebPageLoader("https://example.com/article").load()
text = docs[0].page_content

# Summarize
summary = rlm.run(f"""
Summarize this article in 3 bullet points:

{text}
""")
print(summary)
```

---

## RAG

### PDF Question Answering

```python
from rlm_toolkit import RLM
from rlm_toolkit.loaders import PDFLoader
from rlm_toolkit.splitters import RecursiveTextSplitter
from rlm_toolkit.embeddings import OpenAIEmbeddings
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.retrievers import VectorStoreRetriever

# Load PDF
docs = PDFLoader("company_report.pdf").load()

# Split into chunks
splitter = RecursiveTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = splitter.split_documents(docs)

# Create vector store
embeddings = OpenAIEmbeddings("text-embedding-3-small")
vectorstore = ChromaVectorStore.from_documents(chunks, embeddings)

# Create retriever
retriever = VectorStoreRetriever(vectorstore, search_kwargs={"k": 5})

# Create RLM with retriever
rlm = RLM.from_openai("gpt-4o")
rlm.set_retriever(retriever)
rlm.set_system_prompt("""
Answer based on the provided context only.
Cite sources. If unsure, say "I don't know".
""")

# Ask questions
print(rlm.run("What was the Q3 revenue?"))
print(rlm.run("Who are the key executives?"))
```

### Multi-Document RAG

```python
from rlm_toolkit.loaders import DirectoryLoader, PDFLoader

# Load all PDFs from directory
loader = DirectoryLoader(
    path="./documents",
    glob="**/*.pdf",
    loader_cls=PDFLoader,
    show_progress=True
)
docs = loader.load()

print(f"Loaded {len(docs)} documents")

# Continue with splitting, embedding, etc.
```

### Web RAG

```python
from rlm_toolkit import RLM
from rlm_toolkit.loaders import WebPageLoader
from rlm_toolkit.splitters import MarkdownSplitter
from rlm_toolkit.embeddings import OpenAIEmbeddings
from rlm_toolkit.vectorstores import ChromaVectorStore

# Scrape documentation
urls = [
    "https://docs.example.com/getting-started",
    "https://docs.example.com/api-reference",
    "https://docs.example.com/tutorials"
]

docs = WebPageLoader(urls).load()
chunks = MarkdownSplitter(chunk_size=1000).split_documents(docs)

vectorstore = ChromaVectorStore.from_documents(
    chunks, OpenAIEmbeddings()
)

rlm = RLM.from_openai("gpt-4o")
rlm.set_retriever(vectorstore.as_retriever(k=5))

print(rlm.run("How do I authenticate with the API?"))
```

### Hybrid Search RAG

```python
from rlm_toolkit.retrievers import HybridRetriever

retriever = HybridRetriever(
    vectorstore=vectorstore,
    keyword_weight=0.3,
    semantic_weight=0.7,
    fusion_method="rrf"
)

rlm = RLM.from_openai("gpt-4o")
rlm.set_retriever(retriever)

# Better results for both semantic and keyword queries
print(rlm.run("error code 404"))  # Keyword-heavy
print(rlm.run("How to handle authentication failures"))  # Semantic
```

### RAG with Sources

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")
rlm.set_retriever(retriever)
rlm.set_system_prompt("""
Answer based on context. Format:
1. Answer
2. Sources: [filename:page]
""")

result = rlm.run_with_sources("What is the return policy?")
print(f"Answer: {result.answer}")
print(f"Sources: {result.sources}")
```

### Code Repository RAG

```python
from rlm_toolkit.loaders import GitHubLoader
from rlm_toolkit.splitters import CodeSplitter

# Load code from GitHub
loader = GitHubLoader(
    repo="openai/openai-python",
    file_filter=lambda f: f.endswith(".py")
)
docs = loader.load()

# Code-aware splitting
splitter = CodeSplitter(chunk_size=500, language="python")
chunks = splitter.split_documents(docs)

# Continue with RAG setup...
rlm = RLM.from_openai("gpt-4o")
rlm.set_retriever(vectorstore.as_retriever())

print(rlm.run("How does the chat completion API work?"))
```

---

## Agents

### Research Agent

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import WebSearchTool, WikipediaTool, ArxivTool

agent = ReActAgent.from_openai(
    "gpt-4o",
    tools=[
        WebSearchTool(provider="ddg"),
        WikipediaTool(),
        ArxivTool()
    ]
)

result = agent.run("""
Research the latest developments in quantum computing.
Find recent papers and summarize key breakthroughs.
""")
print(result)
```

### Code Assistant Agent

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import PythonREPL, FileReader, FileWriter

agent = ReActAgent.from_openai(
    "gpt-4o",
    tools=[
        PythonREPL(max_execution_time=30),
        FileReader(),
        FileWriter()
    ],
    system_prompt="You are a Python programming assistant."
)

result = agent.run("""
1. Read the file data.csv
2. Analyze the data using pandas
3. Create a visualization
4. Save the chart as chart.png
""")
```

### Data Analyst Agent

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import PythonREPL, SQLTool

agent = ReActAgent.from_openai(
    "gpt-4o",
    tools=[
        PythonREPL(),
        SQLTool(connection_string="sqlite:///data.db")
    ]
)

result = agent.run("""
Analyze the sales table:
1. Show total revenue by month
2. Find top 10 products
3. Calculate customer retention rate
""")
```

### Web Automation Agent

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import BrowserTool

agent = ReActAgent.from_openai(
    "gpt-4o",
    tools=[BrowserTool()]
)

result = agent.run("""
Go to https://example.com
Fill in the contact form with:
- Name: John Doe
- Email: john@example.com
- Message: Hello!
Submit the form.
""")
```

### Math Solver Agent

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import Tool
import sympy

@Tool(name="solve_equation", description="Solve mathematical equations")
def solve_equation(equation: str) -> str:
    x = sympy.Symbol('x')
    result = sympy.solve(equation, x)
    return str(result)

@Tool(name="differentiate", description="Differentiate expression")
def differentiate(expr: str) -> str:
    x = sympy.Symbol('x')
    result = sympy.diff(expr, x)
    return str(result)

agent = ReActAgent.from_openai("gpt-4o", tools=[solve_equation, differentiate])
print(agent.run("Solve x^2 - 5x + 6 = 0"))
print(agent.run("Find the derivative of x^3 + 2x^2"))
```

### API Integration Agent

```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import Tool
import requests

@Tool(name="get_weather", description="Get weather for a city")
def get_weather(city: str) -> str:
    api_key = "your-api-key"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}"
    response = requests.get(url)
    data = response.json()
    return f"{data['weather'][0]['description']}, {data['main']['temp']}K"

@Tool(name="get_stock", description="Get stock price")
def get_stock(symbol: str) -> str:
    # Your stock API logic
    return f"{symbol}: $150.00"

agent = ReActAgent.from_openai("gpt-4o", tools=[get_weather, get_stock])
result = agent.run("What's the weather in Tokyo and what's the AAPL stock price?")
```

### Streaming Agent

```python
from rlm_toolkit.agents import ReActAgent

agent = ReActAgent.from_openai("gpt-4o", tools=[...])

for event in agent.stream("Research Python async programming"):
    if event.type == "thought":
        print(f"\n💭 {event.content}")
    elif event.type == "action":
        print(f"\n🔧 Using: {event.tool_name}")
    elif event.type == "observation":
        print(f"📋 Result: {event.content[:100]}...")
    elif event.type == "final":
        print(f"\n✅ Answer:\n{event.content}")
```

---

## Memory

### Persistent Chat

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import HierarchicalMemory

memory = HierarchicalMemory(persist_directory="./chat_history")

rlm = RLM.from_openai("gpt-4o", memory=memory)

# Conversation persists across sessions
rlm.run("My name is Alex and I'm learning Python")
# ... restart application ...
rlm.run("What's my name?")  # "Your name is Alex"
```

### Session Manager

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import SessionMemory

sessions = {}

def get_session(user_id: str) -> RLM:
    if user_id not in sessions:
        memory = SessionMemory(session_id=user_id)
        sessions[user_id] = RLM.from_openai("gpt-4o", memory=memory)
    return sessions[user_id]

# Each user has isolated memory
alice = get_session("alice")
bob = get_session("bob")

alice.run("I love cats")
bob.run("I love dogs")

print(alice.run("What do I love?"))  # cats
print(bob.run("What do I love?"))    # dogs
```

### H-MEM (Hierarchical Memory)

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import HierarchicalMemory, HMEMConfig

config = HMEMConfig(
    episode_limit=100,
    consolidation_enabled=True,
    consolidation_threshold=25,
    semantic_clustering=True
)

memory = HierarchicalMemory(config=config, persist_directory="./hmem")
rlm = RLM.from_openai("gpt-4o", memory=memory)

# Memory automatically organizes into:
# - Episodic (recent interactions)
# - Semantic (extracted knowledge)
# - Working (current context)
```

### Conversation Export

```python
from rlm_toolkit.memory import BufferMemory

memory = BufferMemory()
rlm = RLM.from_openai("gpt-4o", memory=memory)

rlm.run("Hello!")
rlm.run("Tell me about Python")
rlm.run("Thanks!")

# Export conversation
history = memory.get_history()
with open("conversation.json", "w") as f:
    json.dump(history, f)

# Load in new session
memory2 = BufferMemory()
memory2.load_history(history)
```

---

## Advanced

### InfiniRetri (1M+ Tokens)

```python
from rlm_toolkit import RLM, RLMConfig
from rlm_toolkit.retrieval import InfiniRetriConfig
from rlm_toolkit.loaders import PDFLoader

# Configure InfiniRetri
config = RLMConfig(
    enable_infiniretri=True,
    infiniretri_config=InfiniRetriConfig(
        chunk_size=4000,
        top_k=5
    ),
    infiniretri_threshold=50000
)

rlm = RLM.from_openai("gpt-4o", config=config)

# Load massive document (1000+ pages)
docs = PDFLoader("massive_report.pdf").load()

# Query with infinite context
result = rlm.run_with_docs(
    query="Find the section about Q3 revenue and explain the growth",
    documents=docs
)
print(result)
```

### Self-Evolving (Challenger-Solver)

```python
from rlm_toolkit.evolve import SelfEvolvingRLM, EvolutionConfig

config = EvolutionConfig(
    strategy="challenger_solver",
    max_iterations=5,
    early_stop_threshold=0.95
)

evolving = SelfEvolvingRLM.from_openai("gpt-4o", config=config)

# Self-improving response
result = evolving.run("""
Write a Python function to efficiently find 
the longest palindromic substring.
Include edge cases and documentation.
""")
print(result)
```

### Multi-Agent Collaboration

```python
from rlm_toolkit.agents.multiagent import MetaMatrix, Agent
from rlm_toolkit import RLM
from rlm_toolkit.tools import WebSearchTool, PythonREPL, FileWriter

# Create specialized agents
researcher = Agent(
    name="researcher",
    description="Searches for information",
    llm=RLM.from_openai("gpt-4o"),
    tools=[WebSearchTool()]
)

analyst = Agent(
    name="analyst", 
    description="Analyzes data with code",
    llm=RLM.from_openai("gpt-4o"),
    tools=[PythonREPL()]
)

writer = Agent(
    name="writer",
    description="Writes reports",
    llm=RLM.from_anthropic("claude-3-sonnet"),
    tools=[FileWriter()]
)

# Create network
matrix = MetaMatrix(topology="mesh", consensus="raft")
matrix.register(researcher)
matrix.register(analyst)
matrix.register(writer)

# Collaborative task
result = matrix.run("""
1. Research AI trends in 2024
2. Analyze the data and create charts
3. Write a comprehensive report
Save everything to output/
""")
```

### Secure Agent with Trust Zones

```python
from rlm_toolkit.agents import SecureAgent, TrustZone
from rlm_toolkit.tools import SecurePythonREPL
from rlm_toolkit.memory import SecureHierarchicalMemory

# Secure code execution
secure_repl = SecurePythonREPL(
    allowed_imports=["math", "json", "datetime"],
    max_execution_time=5,
    enable_network=False,
    sandbox_mode=True
)

# Secure memory
memory = SecureHierarchicalMemory(
    persist_directory="./secure_memory",
    encryption_key="your-256-bit-key",
    trust_zone=TrustZone(name="confidential", level=2)
)

# Secure agent
agent = SecureAgent(
    name="secure_processor",
    trust_zone=TrustZone(name="confidential", level=2),
    tools=[secure_repl],
    memory=memory,
    audit_enabled=True
)

result = agent.run("Process this sensitive data")
```

---

## Production

### FastAPI Application

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from rlm_toolkit import RLM
from rlm_toolkit.memory import SessionMemory
import uuid

app = FastAPI(title="RLM Chat API")

# Store sessions
sessions = {}

class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str

class ChatResponse(BaseModel):
    session_id: str
    response: str

def get_rlm(session_id: str) -> RLM:
    if session_id not in sessions:
        memory = SessionMemory(session_id=session_id)
        sessions[session_id] = RLM.from_openai("gpt-4o", memory=memory)
    return sessions[session_id]

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    rlm = get_rlm(session_id)
    response = rlm.run(request.message)
    return ChatResponse(session_id=session_id, response=response)

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

### Streaming API

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
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  rlm-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

volumes:
  redis-data:
```

### With Redis Caching

```python
from rlm_toolkit import RLM
from rlm_toolkit.cache import RedisCache

cache = RedisCache(
    host="redis",
    port=6379,
    ttl=3600
)

rlm = RLM.from_openai("gpt-4o", cache=cache)

# Responses are cached
response1 = rlm.run("What is Python?")  # API call
response2 = rlm.run("What is Python?")  # From cache (instant)
```

### With Monitoring

```python
from rlm_toolkit import RLM
from rlm_toolkit.callbacks import (
    PrometheusCallback,
    LangfuseCallback,
    TokenCounterCallback
)

callbacks = [
    PrometheusCallback(port=9090),
    LangfuseCallback(
        public_key="pk-...",
        secret_key="sk-..."
    ),
    TokenCounterCallback()
]

rlm = RLM.from_openai("gpt-4o", callbacks=callbacks)
```

---

## Integrations

### Slack Bot

```python
from slack_bolt import App
from rlm_toolkit import RLM
from rlm_toolkit.memory import SessionMemory

app = App(token="xoxb-your-token")
sessions = {}

def get_rlm(user_id: str) -> RLM:
    if user_id not in sessions:
        sessions[user_id] = RLM.from_openai(
            "gpt-4o",
            memory=SessionMemory(session_id=user_id)
        )
    return sessions[user_id]

@app.message(".*")
def handle_message(message, say):
    user_id = message["user"]
    text = message["text"]
    
    rlm = get_rlm(user_id)
    response = rlm.run(text)
    
    say(response)

if __name__ == "__main__":
    app.start(port=3000)
```

### Discord Bot

```python
import discord
from rlm_toolkit import RLM
from rlm_toolkit.memory import SessionMemory

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

sessions = {}

def get_rlm(user_id: int) -> RLM:
    if user_id not in sessions:
        sessions[user_id] = RLM.from_openai(
            "gpt-4o",
            memory=SessionMemory(session_id=str(user_id))
        )
    return sessions[user_id]

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    if client.user.mentioned_in(message):
        rlm = get_rlm(message.author.id)
        response = rlm.run(message.content)
        await message.channel.send(response)

client.run("your-discord-token")
```

### Telegram Bot

```python
from telegram import Update
from telegram.ext import Application, MessageHandler, filters
from rlm_toolkit import RLM
from rlm_toolkit.memory import SessionMemory

sessions = {}

def get_rlm(user_id: int) -> RLM:
    if user_id not in sessions:
        sessions[user_id] = RLM.from_openai(
            "gpt-4o",
            memory=SessionMemory(session_id=str(user_id))
        )
    return sessions[user_id]

async def handle_message(update: Update, context):
    user_id = update.effective_user.id
    text = update.message.text
    
    rlm = get_rlm(user_id)
    response = rlm.run(text)
    
    await update.message.reply_text(response)

app = Application.builder().token("your-telegram-token").build()
app.add_handler(MessageHandler(filters.TEXT, handle_message))
app.run_polling()
```

### Gradio UI

```python
import gradio as gr
from rlm_toolkit import RLM
from rlm_toolkit.memory import BufferMemory

rlm = RLM.from_openai("gpt-4o", memory=BufferMemory())

def chat(message, history):
    response = rlm.run(message)
    return response

demo = gr.ChatInterface(
    chat,
    title="RLM Chat",
    description="Chat with GPT-4o",
    examples=["Hello!", "Explain quantum computing", "Write a poem"]
)

demo.launch()
```

### Streamlit App

```python
import streamlit as st
from rlm_toolkit import RLM
from rlm_toolkit.memory import BufferMemory

st.title("🤖 RLM Chat")

if "rlm" not in st.session_state:
    st.session_state.rlm = RLM.from_openai("gpt-4o", memory=BufferMemory())
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if prompt := st.chat_input("Say something..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    
    response = st.session_state.rlm.run(prompt)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.write(response)
```

---

## Next Steps

- [Tutorials](../tutorials/) - Step-by-step guides
- [Concepts](../concepts/) - Deep dives
- [How-to](../how-to/) - Specific recipes
