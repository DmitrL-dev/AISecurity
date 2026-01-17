# Integrations

RLM-Toolkit integrates with 50+ services across LLM providers, vector databases, embedding models, and observability platforms.

## LLM Providers

### OpenAI

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai(
    model="gpt-4o",  # gpt-4o-mini, o1, o1-mini
    api_key="sk-...",
    temperature=0.7
)
```

**Environment:** `OPENAI_API_KEY`

**Models:** gpt-4o, gpt-4o-mini, o1-preview, o1-mini, gpt-4-turbo

---

### Anthropic

```python
from rlm_toolkit import RLM

rlm = RLM.from_anthropic(
    model="claude-3-sonnet-20240229",
    api_key="sk-ant-..."
)
```

**Environment:** `ANTHROPIC_API_KEY`

**Models:** claude-3-opus, claude-3-sonnet, claude-3-haiku, claude-3-5-sonnet

---

### Google (Gemini)

```python
from rlm_toolkit import RLM

rlm = RLM.from_google(
    model="gemini-1.5-pro",
    api_key="..."
)
```

**Environment:** `GOOGLE_API_KEY`

**Models:** gemini-1.5-pro, gemini-1.5-flash, gemini-pro

---

### Azure OpenAI

```python
from rlm_toolkit import RLM

rlm = RLM.from_azure(
    deployment_name="gpt-4o",
    azure_endpoint="https://your-resource.openai.azure.com/",
    api_key="...",
    api_version="2024-02-01"
)
```

**Environment:** `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`

---

### Ollama (Local)

```python
from rlm_toolkit import RLM

rlm = RLM.from_ollama(
    model="llama3",
    base_url="http://localhost:11434"
)
```

**Models:** llama3, llama3.1, mistral, qwen2, phi3, gemma2

---

### Groq

```python
from rlm_toolkit import RLM

rlm = RLM.from_groq(
    model="llama3-70b-8192",
    api_key="..."
)
```

**Environment:** `GROQ_API_KEY`

**Models:** llama3-70b-8192, llama3-8b-8192, mixtral-8x7b-32768

---

### Together AI

```python
from rlm_toolkit import RLM

rlm = RLM.from_together(
    model="meta-llama/Llama-3-70b-chat-hf",
    api_key="..."
)
```

**Environment:** `TOGETHER_API_KEY`

---

### Mistral

```python
from rlm_toolkit import RLM

rlm = RLM.from_mistral(
    model="mistral-large-latest",
    api_key="..."
)
```

**Environment:** `MISTRAL_API_KEY`

**Models:** mistral-large, mistral-medium, mistral-small, open-mixtral-8x7b

---

### Cohere

```python
from rlm_toolkit import RLM

rlm = RLM.from_cohere(
    model="command-r-plus",
    api_key="..."
)
```

**Environment:** `COHERE_API_KEY`

**Models:** command-r-plus, command-r, command

---

## Vector Databases

### Chroma

```python
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.embeddings import OpenAIEmbeddings

vectorstore = ChromaVectorStore(
    collection_name="my_collection",
    embedding_function=OpenAIEmbeddings(),
    persist_directory="./chroma_db"
)
```

**Install:** `pip install chromadb`

---

### Pinecone

```python
from rlm_toolkit.vectorstores import PineconeVectorStore

vectorstore = PineconeVectorStore(
    index_name="my-index",
    api_key="...",
    environment="us-west1-gcp"
)
```

**Install:** `pip install pinecone-client`

**Environment:** `PINECONE_API_KEY`

---

### Weaviate

```python
from rlm_toolkit.vectorstores import WeaviateVectorStore

vectorstore = WeaviateVectorStore(
    url="http://localhost:8080",
    index_name="Documents"
)
```

**Install:** `pip install weaviate-client`

---

### Qdrant

```python
from rlm_toolkit.vectorstores import QdrantVectorStore

vectorstore = QdrantVectorStore(
    url="http://localhost:6333",
    collection_name="documents"
)
```

**Install:** `pip install qdrant-client`

---

### FAISS

```python
from rlm_toolkit.vectorstores import FAISSVectorStore

vectorstore = FAISSVectorStore.from_documents(
    documents,
    embeddings,
    index_path="./faiss_index"
)
```

**Install:** `pip install faiss-cpu` or `pip install faiss-gpu`

---

### Milvus

```python
from rlm_toolkit.vectorstores import MilvusVectorStore

vectorstore = MilvusVectorStore(
    connection_args={"host": "localhost", "port": "19530"},
    collection_name="documents"
)
```

**Install:** `pip install pymilvus`

---

### PGVector

```python
from rlm_toolkit.vectorstores import PGVectorStore

vectorstore = PGVectorStore(
    connection_string="postgresql://user:pass@localhost/db",
    collection_name="documents"
)
```

**Install:** `pip install pgvector psycopg2`

---

### Redis

```python
from rlm_toolkit.vectorstores import RedisVectorStore

vectorstore = RedisVectorStore(
    redis_url="redis://localhost:6379",
    index_name="documents"
)
```

**Install:** `pip install redis`

---

## Embedding Models

### OpenAI Embeddings

```python
from rlm_toolkit.embeddings import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"  # or text-embedding-3-large
)
```

---

### Cohere Embeddings

```python
from rlm_toolkit.embeddings import CohereEmbeddings

embeddings = CohereEmbeddings(
    model="embed-english-v3.0"
)
```

---

### HuggingFace Embeddings

```python
from rlm_toolkit.embeddings import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)
```

**Install:** `pip install sentence-transformers`

---

### Ollama Embeddings

```python
from rlm_toolkit.embeddings import OllamaEmbeddings

embeddings = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url="http://localhost:11434"
)
```

---

### Voyage AI

```python
from rlm_toolkit.embeddings import VoyageEmbeddings

embeddings = VoyageEmbeddings(
    model="voyage-large-2",
    api_key="..."
)
```

---

### Jina Embeddings

```python
from rlm_toolkit.embeddings import JinaEmbeddings

embeddings = JinaEmbeddings(
    model="jina-embeddings-v2-base-en",
    api_key="..."
)
```

---

## Observability

### Langfuse

```python
from rlm_toolkit.callbacks import LangfuseCallback

callback = LangfuseCallback(
    public_key="pk-...",
    secret_key="sk-...",
    host="https://cloud.langfuse.com"
)

rlm = RLM.from_openai("gpt-4o", callbacks=[callback])
```

**Install:** `pip install langfuse`

---

### Arize Phoenix

```python
from rlm_toolkit.callbacks import PhoenixCallback

callback = PhoenixCallback()

rlm = RLM.from_openai("gpt-4o", callbacks=[callback])
```

**Install:** `pip install arize-phoenix`

---

### OpenTelemetry

```python
from rlm_toolkit.callbacks import OpenTelemetryCallback

callback = OpenTelemetryCallback(
    endpoint="http://localhost:4317"
)
```

---

### Prometheus

```python
from rlm_toolkit.callbacks import PrometheusCallback

callback = PrometheusCallback(
    port=9090,
    prefix="rlm_"
)
```

**Install:** `pip install prometheus-client`

---

### Weights & Biases

```python
from rlm_toolkit.callbacks import WandBCallback

callback = WandBCallback(
    project="my-rlm-project",
    name="experiment-1"
)
```

**Install:** `pip install wandb`

---

## Caching

### Redis Cache

```python
from rlm_toolkit.cache import RedisCache

cache = RedisCache(
    host="localhost",
    port=6379,
    ttl=3600
)

rlm = RLM.from_openai("gpt-4o", cache=cache)
```

---

### SQLite Cache

```python
from rlm_toolkit.cache import SQLiteCache

cache = SQLiteCache(
    database_path="./cache.db"
)
```

---

### InMemory Cache

```python
from rlm_toolkit.cache import InMemoryCache

cache = InMemoryCache(maxsize=1000)
```

---

## Document Loaders

### PDF Libraries

```python
# PyMuPDF (recommended)
from rlm_toolkit.loaders import PDFLoader
loader = PDFLoader("document.pdf", parser="pymupdf")

# Unstructured
loader = PDFLoader("document.pdf", parser="unstructured")

# PyPDF
loader = PDFLoader("document.pdf", parser="pypdf")
```

**Install:** `pip install pymupdf` or `pip install unstructured`

---

### Web Loaders

```python
from rlm_toolkit.loaders import WebPageLoader

# Single page
loader = WebPageLoader("https://example.com")

# Multiple pages
loader = WebPageLoader([
    "https://example.com/page1",
    "https://example.com/page2"
])
```

---

### GitHub Loader

```python
from rlm_toolkit.loaders import GitHubLoader

loader = GitHubLoader(
    repo="owner/repo",
    branch="main",
    token="ghp_...",
    file_filter=lambda f: f.endswith(".py")
)
```

---

## All Integrations Summary

| Category | Integrations |
|----------|-------------|
| **LLM Providers** | OpenAI, Anthropic, Google, Azure, Ollama, Groq, Together, Mistral, Cohere |
| **Vector DBs** | Chroma, Pinecone, Weaviate, Qdrant, FAISS, Milvus, PGVector, Redis |
| **Embeddings** | OpenAI, Cohere, HuggingFace, Ollama, Voyage, Jina, Azure |
| **Observability** | Langfuse, Phoenix, OpenTelemetry, Prometheus, W&B |
| **Cache** | Redis, SQLite, InMemory, Disk |
| **Loaders** | PDF, DOCX, CSV, JSON, HTML, Web, GitHub, YouTube |

---

## Related

- [API Reference](./index.md)
- [Examples](../examples/)
- [Tutorials](../tutorials/)
