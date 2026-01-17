# Векторные хранилища

RLM-Toolkit поддерживает 41 векторное хранилище для семантического поиска и извлечения.

## Поддерживаемые хранилища

### Локальные/Встраиваемые

| Хранилище | Функции | Применение |
|-----------|---------|------------|
| **Chroma** | Встраиваемое, персистентное | Разработка, малые датасеты |
| **FAISS** | CPU/GPU, быстрое | Продакшн, большие датасеты |
| **LanceDB** | Встраиваемое, колоночное | Аналитика + поиск |
| **Qdrant** | Встраиваемое или сервер | Гибкий деплой |
| **SQLite-VSS** | Расширение SQLite | Существующие SQLite приложения |

### Облачные/Управляемые

| Хранилище | Функции | Применение |
|-----------|---------|------------|
| **Pinecone** | Полностью управляемое | Enterprise, масштаб |
| **Weaviate** | GraphQL, гибридный | Графы знаний |
| **Milvus** | Распределённое | Массивный масштаб |
| **Zilliz** | Managed Milvus | Облачный Milvus |
| **Vespa** | Движок Yahoo | Поиск + ML |

### Расширения баз данных

| Хранилище | База данных | Функции |
|-----------|-------------|---------|
| **PGVector** | PostgreSQL | SQL + векторы |
| **Supabase Vector** | Supabase | Auth + векторы |
| **MongoDB Atlas** | MongoDB | Документы + векторы |
| **Redis Stack** | Redis | Кэш + векторы |
| **Elasticsearch** | Elasticsearch | Full-text + векторы |
| **OpenSearch** | OpenSearch | AWS совместимый |
| **SingleStore** | SingleStore | OLTP + векторы |
| **ClickHouse** | ClickHouse | Аналитика + векторы |

## Базовое использование

### Создание векторного хранилища

```python
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.embeddings import OpenAIEmbeddings
from rlm_toolkit.loaders import PDFLoader

# Загрузка документов
docs = PDFLoader("документ.pdf").load()

# Создание эмбеддингов
embeddings = OpenAIEmbeddings("text-embedding-3-small")

# Создание векторного хранилища
vectorstore = ChromaVectorStore.from_documents(
    documents=docs,
    embedding=embeddings,
    collection_name="my_documents",
    persist_directory="./chroma_db"
)
```

### Поиск

```python
# Поиск по схожести
results = vectorstore.similarity_search(
    query="Что такое машинное обучение?",
    k=5
)

for doc in results:
    print(f"Скор: {doc.metadata.get('score', 'N/A')}")
    print(f"Контент: {doc.content[:200]}...")
```

### Со скорами

```python
# Получить скоры схожести
results = vectorstore.similarity_search_with_score(
    query="Что такое машинное обучение?",
    k=5
)

for doc, score in results:
    print(f"Скор: {score:.4f}")
    print(f"Контент: {doc.content[:200]}...")
```

## Типы хранилищ

### Chroma (Рекомендуется для разработки)

```python
from rlm_toolkit.vectorstores import ChromaVectorStore

# Ephemeral (в памяти)
vs = ChromaVectorStore(
    embedding=embeddings,
    collection_name="temp"
)

# Персистентное
vs = ChromaVectorStore(
    embedding=embeddings,
    collection_name="persistent",
    persist_directory="./chroma_db"
)
```

### FAISS (Рекомендуется для продакшна)

```python
from rlm_toolkit.vectorstores import FAISSVectorStore

# Создание из документов
vs = FAISSVectorStore.from_documents(
    documents=docs,
    embedding=embeddings
)

# Сохранение и загрузка
vs.save_local("./faiss_index")
vs = FAISSVectorStore.load_local(
    "./faiss_index", 
    embeddings
)
```

### Pinecone (Облако)

```python
from rlm_toolkit.vectorstores import PineconeVectorStore

vs = PineconeVectorStore(
    index_name="my-index",
    embedding=embeddings,
    api_key="your-pinecone-key",
    environment="us-west1-gcp"
)
```

### PGVector (PostgreSQL)

```python
from rlm_toolkit.vectorstores import PGVectorStore

vs = PGVectorStore(
    embedding=embeddings,
    connection_string="postgresql://user:pass@localhost/db",
    table_name="documents"
)
```

### Qdrant

```python
from rlm_toolkit.vectorstores import QdrantVectorStore

# Локальный
vs = QdrantVectorStore(
    embedding=embeddings,
    path="./qdrant_data",
    collection_name="documents"
)

# Сервер
vs = QdrantVectorStore(
    embedding=embeddings,
    url="http://localhost:6333",
    collection_name="documents"
)
```

## Продвинутые функции

### Фильтрация по метаданным

```python
# Фильтр по метаданным
results = vectorstore.similarity_search(
    query="машинное обучение",
    k=5,
    filter={"category": "technology", "year": {"$gte": 2023}}
)
```

### Гибридный поиск

```python
from rlm_toolkit.vectorstores import WeaviateVectorStore

vs = WeaviateVectorStore(
    embedding=embeddings,
    url="http://localhost:8080"
)

# Комбинация семантики + ключевых слов
results = vs.hybrid_search(
    query="машинное обучение нейронные сети",
    alpha=0.5,  # Баланс: 0=ключевые слова, 1=семантика
    k=5
)
```

### MMR (Maximal Marginal Relevance)

```python
# Разнообразные результаты (уменьшает дублирование)
results = vectorstore.max_marginal_relevance_search(
    query="машинное обучение",
    k=5,
    fetch_k=20,  # Извлечь больше, затем разнообразить
    lambda_mult=0.5  # Фактор разнообразия
)
```

### Пакетные операции

```python
# Добавление документов пакетами
vectorstore.add_documents(
    documents=new_docs,
    batch_size=100
)

# Удаление по ID
vectorstore.delete(ids=["doc1", "doc2"])

# Удаление по фильтру
vectorstore.delete(filter={"category": "old"})
```

## RAG интеграция

```python
from rlm_toolkit import RLM
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.retrievers import VectorStoreRetriever

# Создание retriever из vectorstore
retriever = VectorStoreRetriever(
    vectorstore=vectorstore,
    search_type="similarity",
    search_kwargs={"k": 5}
)

# Использование с RLM
rlm = RLM.from_openai("gpt-4o")
rlm.set_retriever(retriever)

# Теперь запросы автоматически используют RAG
response = rlm.run("Что документ говорит о X?")
```

## Сравнение

| Хранилище | Скорость | Масштаб | Персистентность | Облако | Цена |
|-----------|----------|---------|-----------------|--------|------|
| Chroma | ⭐⭐⭐ | Мал-Сред | ✅ | ❌ | Бесплатно |
| FAISS | ⭐⭐⭐⭐⭐ | Большой | ✅ | ❌ | Бесплатно |
| Pinecone | ⭐⭐⭐⭐ | Огромный | ✅ | ✅ | $$ |
| Qdrant | ⭐⭐⭐⭐ | Большой | ✅ | ✅ | Бесплатно/$ |
| PGVector | ⭐⭐⭐ | Сред-Бол | ✅ | ✅ | $ |
| Weaviate | ⭐⭐⭐⭐ | Большой | ✅ | ✅ | Бесплатно/$ |

## Лучшие практики

!!! tip "Разработка vs Продакшн"
    - **Разработка**: Используйте Chroma (встроенный, простая настройка)
    - **Продакшн**: Используйте FAISS, Qdrant, или Pinecone

!!! tip "Размер индекса"
    - < 100K векторов: Chroma, SQLite-VSS
    - 100K - 10M: FAISS, Qdrant
    - > 10M: Pinecone, Milvus, Weaviate

!!! tip "Гибридный поиск"
    Комбинируйте семантику + ключевые слова для лучшего recall:
    ```python
    results = vs.hybrid_search(query, alpha=0.7)
    ```

!!! tip "Стратегия метаданных"
    Сохраняйте полезные метаданные для фильтрации:
    ```python
    doc.metadata = {
        "source": "report.pdf",
        "page": 5,
        "category": "finance",
        "date": "2024-01-15"
    }
    ```

## Связанное

- [Туториал: RAG Pipeline](../tutorials/03-rag.md)
- [Концепция: Загрузчики](./loaders.md)
- [Туториал: InfiniRetri](../tutorials/06-infiniretri.md)
