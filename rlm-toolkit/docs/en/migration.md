# Migration Guide: LangChain → RLM-Toolkit

This guide helps you migrate existing LangChain code to RLM-Toolkit.

---

## 🎯 Quick Reference

| LangChain | RLM-Toolkit | Notes |
|-----------|-------------|-------|
| `ChatOpenAI(model="gpt-4o")` | `RLM.from_openai("gpt-4o")` | Same parameters |
| `ChatAnthropic(model="claude-3")` | `RLM.from_anthropic("claude-3-sonnet")` | Same parameters |
| `llm.invoke(messages)` | `rlm.run(prompt)` | Simpler API |
| `llm.ainvoke(messages)` | `await rlm.arun(prompt)` | Async |
| `SystemMessage(content=...)` | `rlm.set_system_prompt(...)` | Set once |
| `HumanMessage(content=...)` | Just pass string | No wrapper needed |
| `ConversationBufferMemory` | `BufferMemory` | Same concept |
| `ConversationSummaryMemory` | `SummaryMemory` | Same concept |
| `RecursiveCharacterTextSplitter` | `RecursiveTextSplitter` | Same parameters |
| `PyPDFLoader` | `PDFLoader` | Same interface |
| `DirectoryLoader` | `DirectoryLoader` | Same interface |
| `Chroma.from_documents()` | `ChromaVectorStore.from_documents()` | Same interface |
| `FAISS.from_documents()` | `FAISSVectorStore.from_documents()` | Same interface |
| `vectorstore.as_retriever()` | `vectorstore.as_retriever()` | Identical |
| `RetrievalQA.from_chain_type()` | `RLMConfig(enable_infiniretri=True)` | Simpler |
| `AgentExecutor` | `ReActAgent` | Similar |
| `Tool(func=...)` | `@Tool(...)` decorator | Cleaner syntax |
| `create_react_agent()` | `ReActAgent.from_openai()` | One line |
| `LangSmith` | `LangfuseCallback` | Same purpose |

---

## 📝 Real Migration Examples

### 1. Basic LLM Call

**Before (LangChain):**
```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.7,
    max_tokens=1000
)

messages = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="What is Python?")
]

response = llm.invoke(messages)
print(response.content)
```

**After (RLM-Toolkit):**
```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o", temperature=0.7, max_tokens=1000)
rlm.set_system_prompt("You are a helpful assistant.")

response = rlm.run("What is Python?")
print(response)
```

**Lines of code:** 12 → 5 (**58% reduction**)

---

### 2. Chatbot with Memory

**Before (LangChain):**
```python
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain

llm = ChatOpenAI(model="gpt-4o")
memory = ConversationBufferMemory()

chain = ConversationChain(
    llm=llm,
    memory=memory,
    verbose=True
)

response1 = chain.invoke({"input": "My name is Alex"})
response2 = chain.invoke({"input": "What is my name?"})
```

**After (RLM-Toolkit):**
```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import BufferMemory

rlm = RLM.from_openai("gpt-4o")
rlm.set_memory(BufferMemory())

response1 = rlm.run("My name is Alex")
response2 = rlm.run("What is my name?")  # Remembers: "Alex"
```

**Lines of code:** 13 → 7 (**46% reduction**)

---

### 3. RAG Pipeline

**Before (LangChain):**
```python
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA

# Load
loader = PyPDFLoader("document.pdf")
documents = loader.load()

# Split
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)
chunks = splitter.split_documents(documents)

# Embed
embeddings = OpenAIEmbeddings()
vectorstore = Chroma.from_documents(chunks, embeddings)

# Create chain
llm = ChatOpenAI(model="gpt-4o")
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever
)

# Query
result = qa_chain.invoke("What is the main topic?")
print(result["result"])
```

**After (RLM-Toolkit):**
```python
from rlm_toolkit import RLM, RLMConfig
from rlm_toolkit.loaders import PDFLoader
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.embeddings import OpenAIEmbeddings

# Setup with InfiniRetri for automatic context management
config = RLMConfig(enable_infiniretri=True)
rlm = RLM.from_openai("gpt-4o", config=config)

# Load and index
docs = PDFLoader("document.pdf").load()
vectorstore = ChromaVectorStore.from_documents(docs, OpenAIEmbeddings())
rlm.set_retriever(vectorstore.as_retriever(k=5))

# Query
result = rlm.run("What is the main topic?")
print(result)
```

**Lines of code:** 28 → 12 (**57% reduction**)

---

### 4. Agent with Tools

**Before (LangChain):**
```python
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain import hub

# Define tools
def search(query: str) -> str:
    return f"Results for: {query}"

def calculator(expression: str) -> str:
    return str(eval(expression))

tools = [
    Tool(name="search", description="Search the web", func=search),
    Tool(name="calculator", description="Calculate math", func=calculator),
]

# Create agent
llm = ChatOpenAI(model="gpt-4o")
prompt = hub.pull("hwchase17/react")
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Run
result = agent_executor.invoke({"input": "What is 25 * 4?"})
```

**After (RLM-Toolkit):**
```python
from rlm_toolkit.agents import ReActAgent
from rlm_toolkit.tools import Tool

@Tool(name="search", description="Search the web")
def search(query: str) -> str:
    return f"Results for: {query}"

@Tool(name="calculator", description="Calculate math")
def calculator(expression: str) -> str:
    return str(eval(expression))

# Create agent
agent = ReActAgent.from_openai("gpt-4o", tools=[search, calculator])

# Run
result = agent.run("What is 25 * 4?")
```

**Lines of code:** 22 → 14 (**36% reduction**)

---

## 📦 Import Mapping

```python
# LangChain imports → RLM imports

# LLMs
from langchain_openai import ChatOpenAI
from rlm_toolkit import RLM  # RLM.from_openai()

# Memory
from langchain.memory import ConversationBufferMemory
from rlm_toolkit.memory import BufferMemory

# Loaders
from langchain_community.document_loaders import PyPDFLoader
from rlm_toolkit.loaders import PDFLoader

# Splitters
from langchain.text_splitter import RecursiveCharacterTextSplitter
from rlm_toolkit.splitters import RecursiveTextSplitter

# Vector stores
from langchain_community.vectorstores import Chroma, FAISS
from rlm_toolkit.vectorstores import ChromaVectorStore, FAISSVectorStore

# Embeddings
from langchain_openai import OpenAIEmbeddings
from rlm_toolkit.embeddings import OpenAIEmbeddings  # Same name!

# Agents
from langchain.agents import AgentExecutor
from rlm_toolkit.agents import ReActAgent
```

---

## ⚠️ Breaking Changes

### Things that work differently:

| Aspect | LangChain | RLM-Toolkit |
|--------|-----------|-------------|
| **Message format** | `[HumanMessage(...)]` | Just strings |
| **Chain composition** | `chain1 | chain2` | `pipeline.add_step()` |
| **Callbacks** | `callbacks=[...]` in each call | Set once on RLM instance |
| **Streaming** | `.stream()` method | `stream=True` parameter |

---

## 🔄 Gradual Migration

You don't have to migrate everything at once. RLM and LangChain can coexist:

```python
from langchain_openai import ChatOpenAI
from rlm_toolkit import RLM

# Keep existing LangChain code
langchain_llm = ChatOpenAI(model="gpt-4o")

# New code uses RLM
rlm = RLM.from_openai("gpt-4o")

# Mix in same app
old_result = langchain_llm.invoke([...])
new_result = rlm.run("...")
```

---

## 🎓 Next Steps

After migration:

1. **[Explore InfiniRetri](./concepts/infiniretri.md)** — Handle unlimited context
2. **[Add H-MEM](./concepts/hmem.md)** — Human-like memory
3. **[Security features](./concepts/security.md)** — Built-in protection

---

## See Also

- [Why RLM?](./why-rlm.md) — Comparison with alternatives
- [API Reference](./reference/) — Complete API docs
- [Examples](./examples/) — 150+ production examples
