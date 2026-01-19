# Embeddings

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **Текстовые эмбеддинги** от 15+ провайдеров

## Обзор

RLM-Toolkit поддерживает множество провайдеров эмбеддингов:
- OpenAI (text-embedding-3-large, ada-002)
- Cohere (embed-english-v3.0)
- Google (text-embedding-004)
- HuggingFace (BGE, E5, BAAI)
- Jina AI, Voyage, Mistral
- Локальные модели через Ollama/Sentence Transformers

## Быстрый старт

```python
from rlm_toolkit.embeddings import OpenAIEmbeddings

# Создаём embedder
embedder = OpenAIEmbeddings(model="text-embedding-3-small")

# Эмбеддинг текста
vector = embedder.embed_query("Привет, мир!")
print(f"Размерность: {len(vector)}")  # 1536

# Эмбеддинг нескольких текстов
vectors = embedder.embed_documents([
    "Первый документ",
    "Второй документ",
    "Третий документ"
])
```

## Провайдеры

### OpenAI

```python
from rlm_toolkit.embeddings import OpenAIEmbeddings

# По умолчанию (text-embedding-3-small)
embedder = OpenAIEmbeddings()

# Высокоразмерные
embedder = OpenAIEmbeddings(
    model="text-embedding-3-large",
    dimensions=3072  # или 256, 1024 для экономии
)
```

### Cohere

```python
from rlm_toolkit.embeddings import CohereEmbeddings

embedder = CohereEmbeddings(
    model="embed-english-v3.0",
    input_type="search_document"  # или "search_query"
)
```

### HuggingFace (BGE, E5)

```python
from rlm_toolkit.embeddings import HuggingFaceEmbeddings

# BGE (лучший open-source)
embedder = HuggingFaceEmbeddings(
    model_name="BAAI/bge-large-en-v1.5"
)

# E5
embedder = HuggingFaceEmbeddings(
    model_name="intfloat/e5-large-v2"
)
```

### Ollama (Локальный)

```python
from rlm_toolkit.embeddings import OllamaEmbeddings

# Бесплатно, работает локально
embedder = OllamaEmbeddings(model="nomic-embed-text")
```

### Jina AI

```python
from rlm_toolkit.embeddings import JinaEmbeddings

embedder = JinaEmbeddings(
    model="jina-embeddings-v2-base-en",
    api_key="..."
)
```

### Voyage AI

```python
from rlm_toolkit.embeddings import VoyageEmbeddings

embedder = VoyageEmbeddings(
    model="voyage-large-2",
    api_key="..."
)
```

## Сценарии использования

### RAG Pipeline

```python
from rlm_toolkit.embeddings import OpenAIEmbeddings
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.loaders import PDFLoader

# Загрузка документов
docs = PDFLoader("guide.pdf").load()

# Создание эмбеддингов и хранилища
embedder = OpenAIEmbeddings()
vectorstore = ChromaVectorStore.from_documents(docs, embedder)

# Поиск
results = vectorstore.similarity_search("Как настроить?", k=5)
```

### Семантический поиск

```python
import numpy as np
from rlm_toolkit.embeddings import OpenAIEmbeddings

embedder = OpenAIEmbeddings()

# Корпус
documents = [
    "Python — язык программирования",
    "Франция — страна в Европе",
    "Машинное обучение — раздел AI"
]
doc_vectors = embedder.embed_documents(documents)

# Запрос
query = "Что такое Python?"
query_vector = embedder.embed_query(query)

# Поиск наиболее похожего
similarities = [
    np.dot(query_vector, doc_vec)
    for doc_vec in doc_vectors
]
best_idx = np.argmax(similarities)
print(f"Лучшее совпадение: {documents[best_idx]}")
```

### Кэширование эмбеддингов

```python
from rlm_toolkit.embeddings import OpenAIEmbeddings, CachedEmbeddings

# Оборачиваем в кэш
base = OpenAIEmbeddings()
embedder = CachedEmbeddings(
    base_embeddings=base,
    cache_path="./.embedding_cache"
)

# Первый вызов: вычисляет и кэширует
v1 = embedder.embed_query("Привет")

# Второй вызов: возвращает из кэша (мгновенно, бесплатно)
v2 = embedder.embed_query("Привет")
```

### Пакетная обработка

```python
from rlm_toolkit.embeddings import OpenAIEmbeddings

embedder = OpenAIEmbeddings(
    batch_size=100,  # Обрабатывать 100 за раз
    show_progress=True
)

# Большой датасет
texts = load_million_documents()

# Эффективная пакетная обработка
all_vectors = embedder.embed_documents(texts)
print(f"Обработано {len(all_vectors)} документов")
```

## Сравнение стоимости

| Провайдер | Модель | Стоимость/1M токенов | Размерность |
|-----------|--------|---------------------|-------------|
| OpenAI | text-embedding-3-small | $0.02 | 1536 |
| OpenAI | text-embedding-3-large | $0.13 | 3072 |
| Cohere | embed-english-v3.0 | $0.10 | 1024 |
| Voyage | voyage-large-2 | $0.12 | 1536 |
| Ollama | nomic-embed-text | Бесплатно | 768 |
| HuggingFace | bge-large | Бесплатно | 1024 |

## Связанное

- [Vector Stores](vectorstores.md)
- [RAG Pipeline](rag.md)
- [Туториал: RAG](../tutorials/03-rag.md)
