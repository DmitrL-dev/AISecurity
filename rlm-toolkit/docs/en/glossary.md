# Glossary

<div class="glossary-page">

Welcome to the RLM-Toolkit Glossary! This page explains all key terms and concepts used throughout the documentation.

<input type="text" class="glossary-search" placeholder="🔍 Search terms..." aria-label="Search glossary">

<div class="glossary-grid"></div>

</div>

---

## Core Concepts

### LLM (Large Language Model)
AI model trained on vast text data that can understand and generate human-like text. Examples: GPT-4, Claude, Llama.

```python
rlm = RLM.from_openai("gpt-4o")
```

---

### RAG (Retrieval-Augmented Generation)
Technique where LLM retrieves relevant documents before generating a response. Improves accuracy and allows working with external knowledge.

```python
retriever = vectorstore.as_retriever()
rlm.set_retriever(retriever)
```

---

### Embedding
Numerical representation of text that captures semantic meaning. Similar texts have similar embeddings (close in vector space).

```python
embeddings = OpenAIEmbeddings()
vector = embeddings.embed_query("Hello world")
```

---

### Vector Store
Database optimized for storing and searching vector embeddings. Enables fast similarity search for RAG.

Popular options: **Chroma**, **Pinecone**, **Weaviate**, **FAISS**, **Milvus**

```python
vectorstore = ChromaVectorStore.from_documents(docs, embeddings)
```

---

### Agent
LLM that can use tools and take actions to accomplish tasks autonomously.

```python
agent = ReActAgent.from_openai("gpt-4o", tools=[search, calculator])
result = agent.run("What is the weather in Tokyo?")
```

---

### Tool
Function that an agent can call to interact with external systems.

```python
@Tool(name="search", description="Search the web")
def search(query: str) -> str:
    return search_results
```

---

### Prompt
Text instruction given to an LLM. **System prompt** sets behavior, **user prompt** is the actual request.

```python
rlm.set_system_prompt("You are a helpful coding assistant.")
response = rlm.run("How do I read a file in Python?")
```

---

### Token
Smallest unit of text that LLMs process. ~4 characters or ~0.75 words. Pricing and limits are measured in tokens.

| Model | Context Window |
|-------|----------------|
| GPT-4o | 128K tokens |
| Claude 3 | 200K tokens |
| Gemini 1.5 | 1M tokens |

---

### Context Window
Maximum amount of text an LLM can process at once (input + output combined).

---

### Memory
System for storing and recalling past conversation context.

Types: **Buffer**, **Summary**, **Hierarchical (H-MEM)**

```python
memory = BufferMemory(max_messages=20)
rlm.set_memory(memory)
```

---

## RLM-Specific Concepts

### InfiniRetri
RLM's unique technique for handling unlimited context through dynamic retrieval. Overcomes context window limits.

```python
config = RLMConfig(enable_infiniretri=True)
rlm = RLM.from_openai("gpt-4o", config=config)
```

---

### H-MEM (Hierarchical Memory)
Multi-level memory system inspired by human cognition:
- **Working Memory** — immediate context
- **Episodic Memory** — specific events
- **Semantic Memory** — distilled knowledge

```python
memory = HierarchicalMemory()
memory.add_episode("User asked about Python")
```

---

### Self-Evolving LLM (R-Zero)
LLM that improves its own outputs through reflection using Challenger-Solver architecture.

```python
evolving = SelfEvolvingRLM(challenger="claude-3", solver="gpt-4o")
```

---

### Multi-Agent System
Multiple AI agents collaborating to solve complex tasks.

```python
matrix = MetaMatrix(agents=[researcher, analyst, writer])
```

---

## Document Processing

### Loader
Component that reads documents from various sources (PDF, DOCX, HTML, URLs, etc.).

```python
loader = PDFLoader("document.pdf")
docs = loader.load()
```

---

### Splitter
Breaks large documents into smaller chunks for processing.

```python
splitter = RecursiveTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = splitter.split_documents(docs)
```

---

### Retriever
Component that finds relevant documents for a query.

```python
retriever = vectorstore.as_retriever(k=5)
relevant_docs = retriever.get_relevant_documents(query)
```

---

## Security

### Prompt Injection
Security attack where malicious input hijacks LLM behavior. Example: "Ignore previous instructions..."

```python
detector = PromptInjectionDetector()
result = detector.detect(user_input)
```

---

### Trust Zone
Security boundary that isolates data access in multi-tenant systems.

---

### Guardrails
Safety mechanisms that prevent LLMs from generating harmful or inappropriate content.

---

## Operations

### Callback
Hook that runs during LLM operations for logging, monitoring, cost tracking, etc.

```python
callback = TokenCounterCallback()
rlm = RLM.from_openai("gpt-4o", callbacks=[callback])
```

---

### Observability
Monitoring LLM systems: latency, tokens, errors, traces.

Integrations: **Langfuse**, **Prometheus**, **OpenTelemetry**

---

## See Also

- [Quickstart](./quickstart.md) — Get started in 5 minutes
- [Concepts](./concepts/overview.md) — Deep dive into architecture
- [Tutorials](./tutorials/01-first-app.md) — Step-by-step guides
