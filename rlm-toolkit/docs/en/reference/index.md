# API Reference

Complete API documentation for RLM-Toolkit.

## Quick Links

| Module | Description |
|--------|-------------|
| [RLM](#rlm) | Core language model interface |
| [Providers](#providers) | LLM provider implementations |
| [Memory](#memory) | Memory and conversation management |
| [Loaders](#loaders) | Document loading utilities |
| [Splitters](#splitters) | Text splitting strategies |
| [Embeddings](#embeddings) | Embedding model interfaces |
| [VectorStores](#vectorstores) | Vector database integrations |
| [Retrievers](#retrievers) | Document retrieval systems |
| [Agents](#agents) | Autonomous agent frameworks |
| [Tools](#tools) | Tool definitions and utilities |
| [Callbacks](#callbacks) | Event handling and monitoring |

---

## RLM

The core interface for interacting with language models.

### `RLM`

```python
class RLM:
    """Recursive Language Model - core interface."""
    
    @classmethod
    def from_openai(
        cls,
        model: str = "gpt-4o",
        api_key: str = None,
        temperature: float = 0.7,
        max_tokens: int = None,
        memory: BaseMemory = None,
        callbacks: list[BaseCallback] = None,
        config: RLMConfig = None
    ) -> "RLM":
        """Create RLM from OpenAI."""
    
    @classmethod
    def from_anthropic(
        cls,
        model: str = "claude-3-sonnet",
        api_key: str = None,
        **kwargs
    ) -> "RLM":
        """Create RLM from Anthropic."""
    
    @classmethod
    def from_google(
        cls,
        model: str = "gemini-pro",
        api_key: str = None,
        **kwargs
    ) -> "RLM":
        """Create RLM from Google."""
    
    @classmethod
    def from_ollama(
        cls,
        model: str = "llama3",
        base_url: str = "http://localhost:11434",
        **kwargs
    ) -> "RLM":
        """Create RLM from Ollama (local)."""
    
    def run(
        self,
        prompt: str,
        images: list[str] = None,
        use_cache: bool = True
    ) -> str:
        """Run synchronous completion."""
    
    async def arun(
        self,
        prompt: str,
        images: list[str] = None
    ) -> str:
        """Run async completion."""
    
    def stream(
        self,
        prompt: str
    ) -> Iterator[str]:
        """Stream completion tokens."""
    
    async def astream(
        self,
        prompt: str
    ) -> AsyncIterator[str]:
        """Async stream completion tokens."""
    
    def run_structured(
        self,
        prompt: str,
        output_schema: type[BaseModel]
    ) -> BaseModel:
        """Run with structured Pydantic output."""
    
    def run_with_docs(
        self,
        query: str,
        documents: list[Document]
    ) -> str:
        """Run with document context (InfiniRetri)."""
    
    def set_system_prompt(self, prompt: str) -> None:
        """Set system prompt."""
    
    def set_retriever(self, retriever: BaseRetriever) -> None:
        """Attach retriever for RAG."""
    
    def clear_memory(self) -> None:
        """Clear conversation memory."""
```

### `RLMConfig`

```python
class RLMConfig:
    """Configuration for RLM instances."""
    
    temperature: float = 0.7
    max_tokens: int = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    json_mode: bool = False
    seed: int = None
    
    # InfiniRetri
    enable_infiniretri: bool = False
    infiniretri_config: InfiniRetriConfig = None
    infiniretri_threshold: int = 50000
    
    # Cache
    cache: BaseCache = None
    
    # Timeouts
    timeout: float = 60.0
    max_retries: int = 3
```

---

## Providers

### Supported Providers

| Provider | Class | Models |
|----------|-------|--------|
| OpenAI | `OpenAIProvider` | gpt-4o, gpt-4o-mini, o1, o1-mini |
| Anthropic | `AnthropicProvider` | claude-3-opus, claude-3-sonnet, claude-3-haiku |
| Google | `GoogleProvider` | gemini-pro, gemini-1.5-pro, gemini-1.5-flash |
| Azure | `AzureOpenAIProvider` | Azure-hosted OpenAI models |
| Ollama | `OllamaProvider` | llama3, mistral, qwen, etc. |
| Groq | `GroqProvider` | llama3-70b, mixtral |
| Together | `TogetherProvider` | 100+ open models |
| Cohere | `CohereProvider` | command-r, command-r-plus |
| Mistral | `MistralProvider` | mistral-large, mistral-medium |

### `BaseProvider`

```python
class BaseProvider(ABC):
    """Base class for LLM providers."""
    
    @abstractmethod
    def complete(
        self,
        messages: list[Message],
        **kwargs
    ) -> str:
        """Generate completion."""
    
    @abstractmethod
    async def acomplete(
        self,
        messages: list[Message],
        **kwargs
    ) -> str:
        """Async generate completion."""
    
    @abstractmethod
    def stream(
        self,
        messages: list[Message],
        **kwargs
    ) -> Iterator[str]:
        """Stream completion."""
```

---

## Memory

### `BufferMemory`

```python
class BufferMemory(BaseMemory):
    """Simple in-memory conversation buffer."""
    
    def __init__(
        self,
        max_messages: int = 100,
        return_messages: bool = True
    ):
        pass
    
    def add_user_message(self, content: str) -> None:
        """Add user message."""
    
    def add_assistant_message(self, content: str) -> None:
        """Add assistant message."""
    
    def get_history(self) -> list[Message]:
        """Get conversation history."""
    
    def clear(self) -> None:
        """Clear memory."""
```

### `HierarchicalMemory`

```python
class HierarchicalMemory(BaseMemory):
    """H-MEM: Three-tier hierarchical memory system."""
    
    def __init__(
        self,
        persist_directory: str = None,
        config: HMEMConfig = None
    ):
        pass
    
    def add_episode(self, content: str, metadata: dict = None) -> None:
        """Add episodic memory."""
    
    def consolidate(self) -> None:
        """Consolidate episodic to semantic memory."""
    
    def search(self, query: str, k: int = 5) -> list[Memory]:
        """Search across all memory tiers."""
```

### `HMEMConfig`

```python
class HMEMConfig:
    """Configuration for Hierarchical Memory."""
    
    episode_limit: int = 100
    consolidation_enabled: bool = True
    consolidation_threshold: int = 25
    semantic_clustering: bool = True
    embeddings: BaseEmbeddings = None
```

### `SessionMemory`

```python
class SessionMemory(BaseMemory):
    """Per-session isolated memory."""
    
    def __init__(
        self,
        session_id: str,
        persist: bool = False
    ):
        pass
```

### `SecureHierarchicalMemory`

```python
class SecureHierarchicalMemory(HierarchicalMemory):
    """Encrypted hierarchical memory with trust zones."""
    
    def __init__(
        self,
        encryption_key: str,
        trust_zone: TrustZone = None,
        audit_enabled: bool = False,
        **kwargs
    ):
        pass
```

---

## Loaders

### Document Loaders

| Loader | Formats | Source |
|--------|---------|--------|
| `PDFLoader` | .pdf | Local/URL |
| `DOCXLoader` | .docx | Local |
| `TextLoader` | .txt | Local |
| `CSVLoader` | .csv | Local |
| `JSONLoader` | .json | Local |
| `HTMLLoader` | .html | Local/URL |
| `MarkdownLoader` | .md | Local |
| `WebPageLoader` | web | URL |
| `GitHubLoader` | repo | GitHub |
| `YouTubeLoader` | video | YouTube |
| `DirectoryLoader` | mixed | Directory |

### `BaseLoader`

```python
class BaseLoader(ABC):
    """Base document loader."""
    
    @abstractmethod
    def load(self) -> list[Document]:
        """Load documents."""
    
    def lazy_load(self) -> Iterator[Document]:
        """Lazily load documents."""
```

### `Document`

```python
class Document:
    """Document with content and metadata."""
    
    page_content: str
    metadata: dict[str, Any]
```

---

## Splitters

### `RecursiveTextSplitter`

```python
class RecursiveTextSplitter(BaseSplitter):
    """Recursively split by separators."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: list[str] = ["\n\n", "\n", " ", ""]
    ):
        pass
    
    def split_documents(
        self,
        documents: list[Document]
    ) -> list[Document]:
        """Split documents into chunks."""
```

### Other Splitters

- `TokenTextSplitter` - Split by token count
- `MarkdownSplitter` - Markdown-aware splitting
- `CodeSplitter` - Code-aware splitting
- `HTMLSplitter` - HTML-aware splitting
- `SemanticSplitter` - Semantic similarity splitting

---

## Embeddings

### `BaseEmbeddings`

```python
class BaseEmbeddings(ABC):
    """Base embedding model."""
    
    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed single query."""
    
    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple documents."""
```

### Implementations

| Class | Provider | Models |
|-------|----------|--------|
| `OpenAIEmbeddings` | OpenAI | text-embedding-3-small/large |
| `CohereEmbeddings` | Cohere | embed-english-v3.0 |
| `HuggingFaceEmbeddings` | HuggingFace | sentence-transformers/* |
| `OllamaEmbeddings` | Ollama | nomic-embed-text |
| `VoyageEmbeddings` | Voyage | voyage-large-2 |
| `JinaEmbeddings` | Jina | jina-embeddings-v2 |

---

## VectorStores

### `BaseVectorStore`

```python
class BaseVectorStore(ABC):
    """Base vector store."""
    
    @classmethod
    def from_documents(
        cls,
        documents: list[Document],
        embeddings: BaseEmbeddings
    ) -> "BaseVectorStore":
        """Create from documents."""
    
    def add_documents(self, documents: list[Document]) -> None:
        """Add documents."""
    
    def similarity_search(
        self,
        query: str,
        k: int = 4
    ) -> list[Document]:
        """Search by similarity."""
    
    def as_retriever(self, **kwargs) -> VectorStoreRetriever:
        """Convert to retriever."""
```

### Implementations

| Class | Backend |
|-------|---------|
| `ChromaVectorStore` | Chroma |
| `FAISSVectorStore` | FAISS |
| `PineconeVectorStore` | Pinecone |
| `WeaviateVectorStore` | Weaviate |
| `QdrantVectorStore` | Qdrant |
| `MilvusVectorStore` | Milvus |
| `PGVectorStore` | PostgreSQL |
| `RedisVectorStore` | Redis |

---

## Agents

### `ReActAgent`

```python
class ReActAgent:
    """ReAct pattern agent."""
    
    @classmethod
    def from_openai(
        cls,
        model: str,
        tools: list[BaseTool],
        system_prompt: str = None,
        max_iterations: int = 10
    ) -> "ReActAgent":
        """Create from OpenAI."""
    
    def run(self, task: str) -> str:
        """Execute task."""
    
    def stream(self, task: str) -> Iterator[AgentEvent]:
        """Stream execution events."""
```

### `SecureAgent`

```python
class SecureAgent(ReActAgent):
    """Agent with security features."""
    
    def __init__(
        self,
        trust_zone: TrustZone,
        encryption_enabled: bool = False,
        audit_enabled: bool = False,
        **kwargs
    ):
        pass
```

### Agent Events

```python
class AgentEvent:
    type: str  # "thought", "action", "observation", "final"
    content: str
    tool_name: str = None
    tool_input: str = None
```

---

## Tools

### `@Tool` Decorator

```python
from rlm_toolkit.tools import Tool

@Tool(
    name="calculator",
    description="Calculate math expressions"
)
def calculator(expression: str) -> str:
    return str(eval(expression))
```

### `BaseTool`

```python
class BaseTool(ABC):
    """Base tool class."""
    
    name: str
    description: str
    args_schema: type[BaseModel] = None
    return_direct: bool = False
    
    @abstractmethod
    def run(self, **kwargs) -> str:
        """Execute tool."""
```

### Built-in Tools

- `WebSearchTool` - Web search
- `WikipediaTool` - Wikipedia search
- `ArxivTool` - ArXiv papers
- `PythonREPL` - Python execution
- `SecurePythonREPL` - Sandboxed Python
- `SQLTool` - SQL queries
- `FileReader` - Read files
- `FileWriter` - Write files
- `BrowserTool` - Browser automation

---

## Callbacks

### `BaseCallback`

```python
class BaseCallback(ABC):
    """Base callback handler."""
    
    def on_llm_start(self, prompt: str, **kwargs) -> None:
        pass
    
    def on_llm_end(self, response: str, **kwargs) -> None:
        pass
    
    def on_llm_error(self, error: Exception, **kwargs) -> None:
        pass
    
    def on_tool_start(self, tool_name: str, **kwargs) -> None:
        pass
    
    def on_tool_end(self, output: str, **kwargs) -> None:
        pass
```

### Implementations

| Callback | Purpose |
|----------|---------|
| `ConsoleCallback` | Console logging |
| `TokenCounterCallback` | Token counting |
| `CostCallback` | Cost tracking |
| `LatencyCallback` | Latency monitoring |
| `LangfuseCallback` | Langfuse integration |
| `PhoenixCallback` | Arize Phoenix |
| `PrometheusCallback` | Prometheus metrics |

---

## Next Steps

- [Integrations](./integrations/) - 50+ integrations
- [Examples](../examples/) - 150+ examples
- [Tutorials](../tutorials/) - Step-by-step guides
