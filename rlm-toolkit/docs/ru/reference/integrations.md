# Интеграции

RLM-Toolkit интегрируется с 50+ сервисами: LLM провайдеры, векторные базы, модели эмбеддингов и платформы наблюдаемости.

## LLM Провайдеры

### OpenAI

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai(
    model="gpt-4o",  # gpt-4o-mini, o1, o1-mini
    api_key="sk-...",
    temperature=0.7
)
```

**Переменная окружения:** `OPENAI_API_KEY`

**Модели:** gpt-4o, gpt-4o-mini, o1-preview, o1-mini, gpt-4-turbo

---

### Anthropic

```python
from rlm_toolkit import RLM

rlm = RLM.from_anthropic(
    model="claude-3-sonnet-20240229",
    api_key="sk-ant-..."
)
```

**Переменная окружения:** `ANTHROPIC_API_KEY`

**Модели:** claude-3-opus, claude-3-sonnet, claude-3-haiku, claude-3-5-sonnet

---

### Google (Gemini)

```python
from rlm_toolkit import RLM

rlm = RLM.from_google(
    model="gemini-1.5-pro",
    api_key="..."
)
```

**Переменная окружения:** `GOOGLE_API_KEY`

**Модели:** gemini-1.5-pro, gemini-1.5-flash, gemini-pro

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

**Переменные окружения:** `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`

---

### Ollama (Локальный)

```python
from rlm_toolkit import RLM

rlm = RLM.from_ollama(
    model="llama3",
    base_url="http://localhost:11434"
)
```

**Модели:** llama3, llama3.1, mistral, qwen2, phi3, gemma2

---

### Groq

```python
from rlm_toolkit import RLM

rlm = RLM.from_groq(
    model="llama3-70b-8192",
    api_key="..."
)
```

**Переменная окружения:** `GROQ_API_KEY`

**Модели:** llama3-70b-8192, llama3-8b-8192, mixtral-8x7b-32768

---

### Together AI

```python
from rlm_toolkit import RLM

rlm = RLM.from_together(
    model="meta-llama/Llama-3-70b-chat-hf",
    api_key="..."
)
```

**Переменная окружения:** `TOGETHER_API_KEY`

---

### Mistral

```python
from rlm_toolkit import RLM

rlm = RLM.from_mistral(
    model="mistral-large-latest",
    api_key="..."
)
```

**Переменная окружения:** `MISTRAL_API_KEY`

**Модели:** mistral-large, mistral-medium, mistral-small, open-mixtral-8x7b

---

### Cohere

```python
from rlm_toolkit import RLM

rlm = RLM.from_cohere(
    model="command-r-plus",
    api_key="..."
)
```

**Переменная окружения:** `COHERE_API_KEY`

**Модели:** command-r-plus, command-r, command

---

## Векторные базы данных

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

**Установка:** `pip install chromadb`

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

**Установка:** `pip install pinecone-client`

**Переменная окружения:** `PINECONE_API_KEY`

---

### Weaviate

```python
from rlm_toolkit.vectorstores import WeaviateVectorStore

vectorstore = WeaviateVectorStore(
    url="http://localhost:8080",
    index_name="Documents"
)
```

**Установка:** `pip install weaviate-client`

---

### Qdrant

```python
from rlm_toolkit.vectorstores import QdrantVectorStore

vectorstore = QdrantVectorStore(
    url="http://localhost:6333",
    collection_name="documents"
)
```

**Установка:** `pip install qdrant-client`

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

**Установка:** `pip install faiss-cpu` или `pip install faiss-gpu`

---

### Milvus

```python
from rlm_toolkit.vectorstores import MilvusVectorStore

vectorstore = MilvusVectorStore(
    connection_args={"host": "localhost", "port": "19530"},
    collection_name="documents"
)
```

**Установка:** `pip install pymilvus`

---

### PGVector

```python
from rlm_toolkit.vectorstores import PGVectorStore

vectorstore = PGVectorStore(
    connection_string="postgresql://user:pass@localhost/db",
    collection_name="documents"
)
```

**Установка:** `pip install pgvector psycopg2`

---

### Redis

```python
from rlm_toolkit.vectorstores import RedisVectorStore

vectorstore = RedisVectorStore(
    redis_url="redis://localhost:6379",
    index_name="documents"
)
```

**Установка:** `pip install redis`

---

## Модели эмбеддингов

### OpenAI Embeddings

```python
from rlm_toolkit.embeddings import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"  # или text-embedding-3-large
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

**Установка:** `pip install sentence-transformers`

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

## Наблюдаемость

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

**Установка:** `pip install langfuse`

---

### Arize Phoenix

```python
from rlm_toolkit.callbacks import PhoenixCallback

callback = PhoenixCallback()

rlm = RLM.from_openai("gpt-4o", callbacks=[callback])
```

**Установка:** `pip install arize-phoenix`

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

**Установка:** `pip install prometheus-client`

---

### Weights & Biases

```python
from rlm_toolkit.callbacks import WandBCallback

callback = WandBCallback(
    project="my-rlm-project",
    name="experiment-1"
)
```

**Установка:** `pip install wandb`

---

## Кэширование

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

## Загрузчики документов

### PDF библиотеки

```python
# PyMuPDF (рекомендуется)
from rlm_toolkit.loaders import PDFLoader
loader = PDFLoader("document.pdf", parser="pymupdf")

# Unstructured
loader = PDFLoader("document.pdf", parser="unstructured")

# PyPDF
loader = PDFLoader("document.pdf", parser="pypdf")
```

**Установка:** `pip install pymupdf` или `pip install unstructured`

---

### Web загрузчики

```python
from rlm_toolkit.loaders import WebPageLoader

# Одна страница
loader = WebPageLoader("https://example.com")

# Несколько страниц
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

## Сводка всех интеграций

| Категория | Интеграции |
|-----------|------------|
| **LLM Провайдеры** | OpenAI, Anthropic, Google, Azure, Ollama, Groq, Together, Mistral, Cohere |
| **Векторные БД** | Chroma, Pinecone, Weaviate, Qdrant, FAISS, Milvus, PGVector, Redis |
| **Эмбеддинги** | OpenAI, Cohere, HuggingFace, Ollama, Voyage, Jina, Azure |
| **Наблюдаемость** | Langfuse, Phoenix, OpenTelemetry, Prometheus, W&B |
| **Кэш** | Redis, SQLite, InMemory, Disk |
| **Загрузчики** | PDF, DOCX, CSV, JSON, HTML, Web, GitHub, YouTube |

---

## Связанное

- [Справочник API](./index.md)
- [Примеры](../examples/)
- [Туториалы](../tutorials/)
