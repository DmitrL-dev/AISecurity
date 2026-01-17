# RAG (Retrieval-Augmented Generation)

RAG объединяет генерацию LLM с поиском документов для обоснованных, фактических ответов.

## Что такое RAG?

RAG улучшает LLM путём:
1. **Извлечения** релевантных документов из базы знаний
2. **Дополнения** промпта извлечённым контекстом
3. **Генерации** ответов, основанных на извлечённой информации

```
┌─────────────────────────────────────────────────────────────────┐
│                    RAG Pipeline                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Запрос: "Какова политика компании по удалённой работе?"       │
│              ↓                                                   │
│         [ИЗВЛЕЧЕНИЕ] → Поиск в векторном хранилище              │
│              ↓                                                   │
│        Релевантные документы: [policy.pdf стр 5, hr_manual.pdf] │
│              ↓                                                   │
│         [ДОПОЛНЕНИЕ] → Добавление в промпт                      │
│              ↓                                                   │
│         [ГЕНЕРАЦИЯ] → LLM отвечает с контекстом                 │
│              ↓                                                   │
│        Ответ: "Согласно HR политике..."                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Базовый RAG

```python
from rlm_toolkit import RLM
from rlm_toolkit.loaders import PDFLoader
from rlm_toolkit.splitters import RecursiveTextSplitter
from rlm_toolkit.embeddings import OpenAIEmbeddings
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.retrievers import VectorStoreRetriever

# 1. Загрузка документов
docs = PDFLoader("company_policy.pdf").load()

# 2. Разбиение на чанки
splitter = RecursiveTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = splitter.split_documents(docs)

# 3. Создание эмбеддингов и сохранение
embeddings = OpenAIEmbeddings("text-embedding-3-small")
vectorstore = ChromaVectorStore.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="./db"
)

# 4. Создание retriever
retriever = VectorStoreRetriever(
    vectorstore=vectorstore,
    search_type="similarity",
    search_kwargs={"k": 5}
)

# 5. Использование с RLM
rlm = RLM.from_openai("gpt-4o")
rlm.set_retriever(retriever)

# 6. Запрос
response = rlm.run("Какова политика удалённой работы?")
print(response)
```

## Компоненты RAG

### Загрузчики документов

Загрузка документов из различных источников:

```python
from rlm_toolkit.loaders import (
    PDFLoader,
    DOCXLoader,
    WebPageLoader,
    DirectoryLoader
)

# Один файл
docs = PDFLoader("report.pdf").load()

# Вся директория
docs = DirectoryLoader("./docs", glob="**/*.pdf").load()

# Веб-страницы
docs = WebPageLoader("https://example.com/docs").load()
```

### Разделители текста

Разбиение документов на чанки:

```python
from rlm_toolkit.splitters import (
    RecursiveTextSplitter,
    TokenTextSplitter,
    MarkdownSplitter,
    CodeSplitter
)

# Общего назначения
splitter = RecursiveTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", " ", ""]
)

# На основе токенов (рекомендуется для моделей)
splitter = TokenTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    model="gpt-4o"
)

# Markdown-aware
splitter = MarkdownSplitter(
    chunk_size=1000,
    headers_to_split_on=["#", "##"]
)

# Code-aware
splitter = CodeSplitter(
    chunk_size=500,
    language="python"
)
```

### Эмбеддинги

Преобразование текста в векторы:

```python
from rlm_toolkit.embeddings import (
    OpenAIEmbeddings,
    CohereEmbeddings,
    HuggingFaceEmbeddings,
    OllamaEmbeddings
)

# OpenAI
embeddings = OpenAIEmbeddings("text-embedding-3-small")

# Cohere
embeddings = CohereEmbeddings("embed-english-v3.0")

# Локальные
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# Ollama
embeddings = OllamaEmbeddings(model="nomic-embed-text")
```

### Векторные хранилища

Хранение и поиск эмбеддингов:

```python
from rlm_toolkit.vectorstores import (
    ChromaVectorStore,
    FAISSVectorStore,
    PineconeVectorStore,
    QdrantVectorStore
)

# Chroma (разработка)
vs = ChromaVectorStore.from_documents(docs, embeddings)

# FAISS (продакшн)
vs = FAISSVectorStore.from_documents(docs, embeddings)

# Pinecone (облако)
vs = PineconeVectorStore(index_name="my-index", embedding=embeddings)
```

### Ретриверы

Стратегии поиска:

```python
from rlm_toolkit.retrievers import (
    VectorStoreRetriever,
    MultiQueryRetriever,
    SelfQueryRetriever,
    ContextualCompressionRetriever
)

# Базовый ретривер
retriever = VectorStoreRetriever(vectorstore, search_kwargs={"k": 5})

# Multi-query (генерирует несколько запросов для лучшего recall)
retriever = MultiQueryRetriever(
    vectorstore=vectorstore,
    llm=RLM.from_openai("gpt-4o-mini"),
    num_queries=3
)

# Self-query (извлекает фильтр из естественного языка)
retriever = SelfQueryRetriever(
    vectorstore=vectorstore,
    llm=RLM.from_openai("gpt-4o-mini"),
    metadata_fields=["category", "date", "author"]
)

# Compression (суммирует извлечённые документы)
retriever = ContextualCompressionRetriever(
    vectorstore=vectorstore,
    compressor=RLM.from_openai("gpt-4o-mini")
)
```

## Продвинутые паттерны RAG

### Гибридный поиск

Комбинация семантика + ключевые слова:

```python
from rlm_toolkit.retrievers import HybridRetriever

retriever = HybridRetriever(
    vectorstore=vectorstore,
    keyword_weight=0.3,      # 30% ключевые слова
    semantic_weight=0.7,     # 70% семантика
    fusion_method="rrf"       # Reciprocal Rank Fusion
)
```

### Реранкинг

```python
from rlm_toolkit.retrievers import ReRankRetriever

retriever = ReRankRetriever(
    base_retriever=vectorstore.as_retriever(k=20),
    reranker="cross-encoder/ms-marco-MiniLM-L-12-v2",
    top_k=5
)
```

### Parent Document Retriever

```python
from rlm_toolkit.retrievers import ParentDocumentRetriever

# Извлекает дочерние чанки, возвращает родительские документы
retriever = ParentDocumentRetriever(
    vectorstore=vectorstore,
    child_splitter=RecursiveTextSplitter(chunk_size=200),
    parent_splitter=RecursiveTextSplitter(chunk_size=2000)
)
```

### Ensemble Retriever

```python
from rlm_toolkit.retrievers import EnsembleRetriever

# Комбинирование нескольких ретриверов
retriever = EnsembleRetriever(
    retrievers=[
        retriever_1,  # Векторный поиск
        retriever_2,  # BM25
        retriever_3,  # Ключевые слова
    ],
    weights=[0.5, 0.3, 0.2]
)
```

## RAG с InfiniRetri

Для документов > 50K токенов:

```python
from rlm_toolkit import RLM, RLMConfig
from rlm_toolkit.retrieval import InfiniRetriConfig

config = RLMConfig(
    enable_infiniretri=True,
    infiniretri_config=InfiniRetriConfig(
        chunk_size=4000,
        chunk_overlap=200,
        top_k=5
    ),
    infiniretri_threshold=50000
)

rlm = RLM.from_openai("gpt-4o", config=config)

# Автоматически использует InfiniRetri для длинных документов
response = rlm.run_with_docs(
    query="Суммируй ключевые моменты",
    documents=very_long_documents  # 1M+ токенов
)
```

## Оценка RAG

```python
from rlm_toolkit.evaluation import RAGEvaluator

evaluator = RAGEvaluator(
    retriever=retriever,
    generator=rlm
)

results = evaluator.evaluate(
    questions=["Что такое X?", "Как работает Y?"],
    ground_truth=["X это...", "Y работает путём..."],
    metrics=["answer_relevancy", "faithfulness", "context_recall"]
)

print(results)
# {
#   "answer_relevancy": 0.85,
#   "faithfulness": 0.92,
#   "context_recall": 0.78
# }
```

## Лучшие практики

!!! tip "Стратегия чанкинга"
    - Размер чанка: 500-1000 токенов для большинства случаев
    - Включайте перекрытие (10-20%) для непрерывности контекста
    - Используйте семантические разделители для лучших границ

!!! tip "Качество извлечения"
    - Начинайте с k=5-10 документов
    - Используйте гибридный поиск для лучшего recall
    - Реранкинг для precision

!!! tip "Дизайн промптов"
    - Включайте ссылки на источники в промпт
    - Просите модель цитировать из контекста
    - Инструктируйте говорить "Не знаю" при неуверенности

!!! tip "Оценка"
    - Тестируйте с ground truth ответами
    - Мониторьте faithfulness (галлюцинации)
    - Отслеживайте релевантность контекста

## Связанное

- [Туториал: RAG Pipeline](../tutorials/03-rag.md)
- [Туториал: InfiniRetri](../tutorials/06-infiniretri.md)
- [Концепция: Загрузчики](./loaders.md)
- [Концепция: Векторные хранилища](./vectorstores.md)
