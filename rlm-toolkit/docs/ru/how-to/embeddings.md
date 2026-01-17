# How-to: Настройка эмбеддингов

Рецепты настройки моделей эмбеддингов.

## OpenAI эмбеддинги

```python
from rlm_toolkit.embeddings import OpenAIEmbeddings

# По умолчанию
embeddings = OpenAIEmbeddings("text-embedding-3-small")

# С опциями
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large",
    dimensions=1024,  # Уменьшение размерности
    api_key="your-key"
)

# Эмбеддинг текста
vector = embeddings.embed_query("Привет мир")
print(f"Размерность: {len(vector)}")

# Эмбеддинг документов
vectors = embeddings.embed_documents([
    "Документ 1",
    "Документ 2"
])
```

## Cohere эмбеддинги

```python
from rlm_toolkit.embeddings import CohereEmbeddings

embeddings = CohereEmbeddings(
    model="embed-english-v3.0",
    input_type="search_document"  # или "search_query"
)
```

## Локальные эмбеддинги (HuggingFace)

```python
from rlm_toolkit.embeddings import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    device="cuda"  # или "cpu"
)

# Мультиязычные
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
```

## Ollama эмбеддинги (локальные)

```python
from rlm_toolkit.embeddings import OllamaEmbeddings

embeddings = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url="http://localhost:11434"
)
```

## Azure OpenAI эмбеддинги

```python
from rlm_toolkit.embeddings import AzureOpenAIEmbeddings

embeddings = AzureOpenAIEmbeddings(
    deployment_name="text-embedding-ada-002",
    api_key="your-azure-key",
    api_version="2024-02-15-preview",
    azure_endpoint="https://your-resource.openai.azure.com"
)
```

## Google эмбеддинги

```python
from rlm_toolkit.embeddings import GoogleEmbeddings

embeddings = GoogleEmbeddings(
    model="models/embedding-001",
    api_key="your-google-key"
)
```

## Voyage AI эмбеддинги

```python
from rlm_toolkit.embeddings import VoyageEmbeddings

embeddings = VoyageEmbeddings(
    model="voyage-large-2",
    api_key="your-voyage-key"
)
```

## Jina эмбеддинги

```python
from rlm_toolkit.embeddings import JinaEmbeddings

embeddings = JinaEmbeddings(
    model="jina-embeddings-v2-base-en",
    api_key="your-jina-key"
)
```

## Кэширование эмбеддингов

```python
from rlm_toolkit.embeddings import CachedEmbeddings

cached = CachedEmbeddings(
    embeddings=OpenAIEmbeddings("text-embedding-3-small"),
    cache_dir="./embedding_cache"
)

# Первый вызов вычисляет, последующие используют кэш
vector = cached.embed_query("Привет")
vector = cached.embed_query("Привет")  # Из кэша
```

## Сравнение

| Модель | Размерность | Скорость | Качество | Цена |
|--------|-------------|----------|----------|------|
| text-embedding-3-small | 1536 | Быстро | ⭐⭐⭐⭐ | $ |
| text-embedding-3-large | 3072 | Средне | ⭐⭐⭐⭐⭐ | $$ |
| all-MiniLM-L6-v2 | 384 | Быстро | ⭐⭐⭐ | Бесплатно |
| nomic-embed-text | 768 | Быстро | ⭐⭐⭐⭐ | Бесплатно |

## Связанное

- [Концепция: Векторные хранилища](../concepts/vectorstores.md)
- [How-to: Векторные хранилища](./vectorstores.md)
