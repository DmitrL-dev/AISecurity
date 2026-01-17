# Справочник API

Полная API документация для RLM-Toolkit.

## Быстрая навигация

| Модуль | Описание |
|--------|----------|
| [RLM](#rlm) | Основной интерфейс языковых моделей |
| [Providers](#providers) | Реализации LLM провайдеров |
| [Memory](#memory) | Память и управление разговорами |
| [Loaders](#loaders) | Утилиты загрузки документов |
| [Splitters](#splitters) | Стратегии разбиения текста |
| [Embeddings](#embeddings) | Интерфейсы моделей эмбеддингов |
| [VectorStores](#vectorstores) | Интеграции векторных баз |
| [Retrievers](#retrievers) | Системы извлечения документов |
| [Agents](#agents) | Фреймворки автономных агентов |
| [Tools](#tools) | Определения инструментов |
| [Callbacks](#callbacks) | Обработка событий и мониторинг |

---

## RLM

Основной интерфейс для работы с языковыми моделями.

### `RLM`

```python
class RLM:
    """Recursive Language Model - основной интерфейс."""
    
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
        """Создать RLM из OpenAI."""
    
    @classmethod
    def from_anthropic(
        cls,
        model: str = "claude-3-sonnet",
        api_key: str = None,
        **kwargs
    ) -> "RLM":
        """Создать RLM из Anthropic."""
    
    @classmethod
    def from_google(
        cls,
        model: str = "gemini-pro",
        api_key: str = None,
        **kwargs
    ) -> "RLM":
        """Создать RLM из Google."""
    
    @classmethod
    def from_ollama(
        cls,
        model: str = "llama3",
        base_url: str = "http://localhost:11434",
        **kwargs
    ) -> "RLM":
        """Создать RLM из Ollama (локальный)."""
    
    def run(
        self,
        prompt: str,
        images: list[str] = None,
        use_cache: bool = True
    ) -> str:
        """Синхронное завершение."""
    
    async def arun(
        self,
        prompt: str,
        images: list[str] = None
    ) -> str:
        """Асинхронное завершение."""
    
    def stream(
        self,
        prompt: str
    ) -> Iterator[str]:
        """Потоковая передача токенов."""
    
    async def astream(
        self,
        prompt: str
    ) -> AsyncIterator[str]:
        """Асинхронная потоковая передача."""
    
    def run_structured(
        self,
        prompt: str,
        output_schema: type[BaseModel]
    ) -> BaseModel:
        """Запуск со структурированным Pydantic выводом."""
    
    def run_with_docs(
        self,
        query: str,
        documents: list[Document]
    ) -> str:
        """Запуск с контекстом документов (InfiniRetri)."""
    
    def set_system_prompt(self, prompt: str) -> None:
        """Установить системный промпт."""
    
    def set_retriever(self, retriever: BaseRetriever) -> None:
        """Присоединить ретривер для RAG."""
    
    def clear_memory(self) -> None:
        """Очистить память разговора."""
```

### `RLMConfig`

```python
class RLMConfig:
    """Конфигурация для экземпляров RLM."""
    
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
    
    # Кэш
    cache: BaseCache = None
    
    # Таймауты
    timeout: float = 60.0
    max_retries: int = 3
```

---

## Providers

### Поддерживаемые провайдеры

| Провайдер | Класс | Модели |
|-----------|-------|--------|
| OpenAI | `OpenAIProvider` | gpt-4o, gpt-4o-mini, o1, o1-mini |
| Anthropic | `AnthropicProvider` | claude-3-opus, claude-3-sonnet, claude-3-haiku |
| Google | `GoogleProvider` | gemini-pro, gemini-1.5-pro, gemini-1.5-flash |
| Azure | `AzureOpenAIProvider` | Модели OpenAI на Azure |
| Ollama | `OllamaProvider` | llama3, mistral, qwen и др. |
| Groq | `GroqProvider` | llama3-70b, mixtral |
| Together | `TogetherProvider` | 100+ открытых моделей |
| Cohere | `CohereProvider` | command-r, command-r-plus |
| Mistral | `MistralProvider` | mistral-large, mistral-medium |

### `BaseProvider`

```python
class BaseProvider(ABC):
    """Базовый класс для LLM провайдеров."""
    
    @abstractmethod
    def complete(
        self,
        messages: list[Message],
        **kwargs
    ) -> str:
        """Генерация завершения."""
    
    @abstractmethod
    async def acomplete(
        self,
        messages: list[Message],
        **kwargs
    ) -> str:
        """Асинхронная генерация завершения."""
    
    @abstractmethod
    def stream(
        self,
        messages: list[Message],
        **kwargs
    ) -> Iterator[str]:
        """Потоковое завершение."""
```

---

## Memory

### `BufferMemory`

```python
class BufferMemory(BaseMemory):
    """Простой буфер разговора в памяти."""
    
    def __init__(
        self,
        max_messages: int = 100,
        return_messages: bool = True
    ):
        pass
    
    def add_user_message(self, content: str) -> None:
        """Добавить сообщение пользователя."""
    
    def add_assistant_message(self, content: str) -> None:
        """Добавить сообщение ассистента."""
    
    def get_history(self) -> list[Message]:
        """Получить историю разговора."""
    
    def clear(self) -> None:
        """Очистить память."""
```

### `HierarchicalMemory`

```python
class HierarchicalMemory(BaseMemory):
    """H-MEM: Трёхуровневая иерархическая система памяти."""
    
    def __init__(
        self,
        persist_directory: str = None,
        config: HMEMConfig = None
    ):
        pass
    
    def add_episode(self, content: str, metadata: dict = None) -> None:
        """Добавить эпизодическую память."""
    
    def consolidate(self) -> None:
        """Консолидировать эпизодическую в семантическую память."""
    
    def search(self, query: str, k: int = 5) -> list[Memory]:
        """Поиск по всем уровням памяти."""
```

### `HMEMConfig`

```python
class HMEMConfig:
    """Конфигурация для иерархической памяти."""
    
    episode_limit: int = 100
    consolidation_enabled: bool = True
    consolidation_threshold: int = 25
    semantic_clustering: bool = True
    embeddings: BaseEmbeddings = None
```

### `SessionMemory`

```python
class SessionMemory(BaseMemory):
    """Изолированная память по сессиям."""
    
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
    """Зашифрованная иерархическая память с зонами доверия."""
    
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

### Загрузчики документов

| Загрузчик | Форматы | Источник |
|-----------|---------|----------|
| `PDFLoader` | .pdf | Локальный/URL |
| `DOCXLoader` | .docx | Локальный |
| `TextLoader` | .txt | Локальный |
| `CSVLoader` | .csv | Локальный |
| `JSONLoader` | .json | Локальный |
| `HTMLLoader` | .html | Локальный/URL |
| `MarkdownLoader` | .md | Локальный |
| `WebPageLoader` | web | URL |
| `GitHubLoader` | repo | GitHub |
| `YouTubeLoader` | video | YouTube |
| `DirectoryLoader` | смешанный | Директория |

### `BaseLoader`

```python
class BaseLoader(ABC):
    """Базовый загрузчик документов."""
    
    @abstractmethod
    def load(self) -> list[Document]:
        """Загрузить документы."""
    
    def lazy_load(self) -> Iterator[Document]:
        """Ленивая загрузка документов."""
```

### `Document`

```python
class Document:
    """Документ с контентом и метаданными."""
    
    page_content: str
    metadata: dict[str, Any]
```

---

## Splitters

### `RecursiveTextSplitter`

```python
class RecursiveTextSplitter(BaseSplitter):
    """Рекурсивное разбиение по разделителям."""
    
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
        """Разбить документы на чанки."""
```

### Другие разделители

- `TokenTextSplitter` - Разбиение по количеству токенов
- `MarkdownSplitter` - Markdown-aware разбиение
- `CodeSplitter` - Code-aware разбиение
- `HTMLSplitter` - HTML-aware разбиение
- `SemanticSplitter` - Семантическое разбиение

---

## Embeddings

### `BaseEmbeddings`

```python
class BaseEmbeddings(ABC):
    """Базовая модель эмбеддингов."""
    
    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Эмбеддинг одного запроса."""
    
    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Эмбеддинг нескольких документов."""
```

### Реализации

| Класс | Провайдер | Модели |
|-------|-----------|--------|
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
    """Базовое векторное хранилище."""
    
    @classmethod
    def from_documents(
        cls,
        documents: list[Document],
        embeddings: BaseEmbeddings
    ) -> "BaseVectorStore":
        """Создать из документов."""
    
    def add_documents(self, documents: list[Document]) -> None:
        """Добавить документы."""
    
    def similarity_search(
        self,
        query: str,
        k: int = 4
    ) -> list[Document]:
        """Поиск по схожести."""
    
    def as_retriever(self, **kwargs) -> VectorStoreRetriever:
        """Преобразовать в ретривер."""
```

### Реализации

| Класс | Бэкенд |
|-------|--------|
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
    """Агент по паттерну ReAct."""
    
    @classmethod
    def from_openai(
        cls,
        model: str,
        tools: list[BaseTool],
        system_prompt: str = None,
        max_iterations: int = 10
    ) -> "ReActAgent":
        """Создать из OpenAI."""
    
    def run(self, task: str) -> str:
        """Выполнить задачу."""
    
    def stream(self, task: str) -> Iterator[AgentEvent]:
        """Потоковая передача событий выполнения."""
```

### `SecureAgent`

```python
class SecureAgent(ReActAgent):
    """Агент с функциями безопасности."""
    
    def __init__(
        self,
        trust_zone: TrustZone,
        encryption_enabled: bool = False,
        audit_enabled: bool = False,
        **kwargs
    ):
        pass
```

### События агента

```python
class AgentEvent:
    type: str  # "thought", "action", "observation", "final"
    content: str
    tool_name: str = None
    tool_input: str = None
```

---

## Tools

### Декоратор `@Tool`

```python
from rlm_toolkit.tools import Tool

@Tool(
    name="calculator",
    description="Вычислить математические выражения"
)
def calculator(expression: str) -> str:
    return str(eval(expression))
```

### `BaseTool`

```python
class BaseTool(ABC):
    """Базовый класс инструмента."""
    
    name: str
    description: str
    args_schema: type[BaseModel] = None
    return_direct: bool = False
    
    @abstractmethod
    def run(self, **kwargs) -> str:
        """Выполнить инструмент."""
```

### Встроенные инструменты

- `WebSearchTool` - Веб-поиск
- `WikipediaTool` - Поиск по Wikipedia
- `ArxivTool` - Статьи ArXiv
- `PythonREPL` - Выполнение Python
- `SecurePythonREPL` - Изолированный Python
- `SQLTool` - SQL запросы
- `FileReader` - Чтение файлов
- `FileWriter` - Запись файлов
- `BrowserTool` - Автоматизация браузера

---

## Callbacks

### `BaseCallback`

```python
class BaseCallback(ABC):
    """Базовый обработчик callback."""
    
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

### Реализации

| Callback | Назначение |
|----------|------------|
| `ConsoleCallback` | Логирование в консоль |
| `TokenCounterCallback` | Подсчёт токенов |
| `CostCallback` | Отслеживание стоимости |
| `LatencyCallback` | Мониторинг латентности |
| `LangfuseCallback` | Интеграция Langfuse |
| `PhoenixCallback` | Arize Phoenix |
| `PrometheusCallback` | Метрики Prometheus |

---

## Дальнейшие шаги

- [Интеграции](./integrations/) - 50+ интеграций
- [Примеры](../examples/) - 150+ примеров
- [Туториалы](../tutorials/) - Пошаговые руководства
