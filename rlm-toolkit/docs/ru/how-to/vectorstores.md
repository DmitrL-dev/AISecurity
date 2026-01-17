# How-to: Настройка векторных хранилищ

Рецепты настройки и использования векторных хранилищ.

## Chroma (разработка)

```python
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.embeddings import OpenAIEmbeddings

embeddings = OpenAIEmbeddings("text-embedding-3-small")

# В памяти
vs = ChromaVectorStore(
    embedding=embeddings,
    collection_name="temp"
)

# Персистентное
vs = ChromaVectorStore(
    embedding=embeddings,
    collection_name="docs",
    persist_directory="./chroma_db"
)
```

## FAISS (продакшн)

```python
from rlm_toolkit.vectorstores import FAISSVectorStore

vs = FAISSVectorStore.from_documents(docs, embeddings)

# Сохранение
vs.save_local("./faiss_index")

# Загрузка
vs = FAISSVectorStore.load_local("./faiss_index", embeddings)
```

## Pinecone (облако)

```python
from rlm_toolkit.vectorstores import PineconeVectorStore

vs = PineconeVectorStore(
    index_name="my-index",
    embedding=embeddings,
    api_key="your-key",
    environment="us-west1-gcp"
)
```

## PGVector (PostgreSQL)

```python
from rlm_toolkit.vectorstores import PGVectorStore

vs = PGVectorStore(
    embedding=embeddings,
    connection_string="postgresql://user:pass@localhost/db",
    table_name="documents"
)
```

## Qdrant

```python
from rlm_toolkit.vectorstores import QdrantVectorStore

# Локальный
vs = QdrantVectorStore(
    embedding=embeddings,
    path="./qdrant_data",
    collection_name="docs"
)

# Сервер
vs = QdrantVectorStore(
    embedding=embeddings,
    url="http://localhost:6333",
    collection_name="docs"
)
```

## Добавление документов

```python
vs.add_documents(documents)
```

## Поиск

```python
# Поиск по схожести
results = vs.similarity_search("query", k=5)

# Со скорами
results = vs.similarity_search_with_score("query", k=5)

# С фильтром по метаданным
results = vs.similarity_search(
    "query",
    k=5,
    filter={"category": "tech"}
)
```

## MMR поиск (разнообразие)

```python
results = vs.max_marginal_relevance_search(
    "query",
    k=5,
    fetch_k=20,
    lambda_mult=0.5
)
```

## Удаление документов

```python
vs.delete(ids=["doc1", "doc2"])
vs.delete(filter={"category": "old"})
```

## Связанное

- [Концепция: Векторные хранилища](../concepts/vectorstores.md)
- [Туториал: RAG](../tutorials/03-rag.md)
