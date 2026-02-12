# Туториал 3: RAG Pipeline

Создайте полноценную систему Retrieval-Augmented Generation (RAG) для ответов на вопросы по документам.

## Что вы создадите

RAG-систему, которая:

1. Загружает PDF и другие документы
2. Разбивает и создаёт эмбеддинги контента
3. Сохраняет в векторную базу данных
4. Извлекает релевантный контекст для запросов
5. Генерирует точные ответы

## Понимание RAG

```
┌─────────────────────────────────────────────────────────────────┐
│                        RAG Pipeline                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Документ → Загрузчик → Сплиттер → Эмбеддинги → ВекторноеХранилище│
│                                                     ↓            │
│   Запрос → Эмбеддинги → Ретривер → Контекст + Запрос → LLM → Ответ│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Предварительные требования

```bash
pip install rlm-toolkit[all]
export OPENAI_API_KEY=your-key
```

## Шаг 1: Загрузка документов

RLM-Toolkit поддерживает 135+ загрузчиков документов:

```python
from rlm_toolkit.loaders import (
    PDFLoader,
    TextLoader,
    DOCXLoader,
    MarkdownLoader,
    WebPageLoader
)

# Загружаем PDF
pdf_docs = PDFLoader("отчёт.pdf").load()
print(f"Загружено {len(pdf_docs)} страниц")

# Загружаем веб-страницу
web_docs = WebPageLoader("https://example.com/article").load()

# Загружаем несколько файлов
from rlm_toolkit.loaders import DirectoryLoader

all_docs = DirectoryLoader(
    "./documents",
    glob="**/*.pdf",
    loader_cls=PDFLoader
).load()
```

## Шаг 2: Разбиение документов

Большие документы нужно разбить на меньшие чанки:

```python
from rlm_toolkit.splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,       # Символов на чанк
    chunk_overlap=200,     # Перекрытие между чанками
    separators=["\n\n", "\n", ". ", " ", ""]
)

chunks = splitter.split_documents(pdf_docs)
print(f"Создано {len(chunks)} чанков")
```

### Выбор параметров чанков

| Тип документа | chunk_size | chunk_overlap |
|---------------|------------|---------------|
| Техническая документация | 1000-1500 | 200 |
| Юридические документы | 500-800 | 100 |
| Разговоры | 200-400 | 50 |
| Код | 1500-2000 | 300 |

## Шаг 3: Создание эмбеддингов

```python
from rlm_toolkit.embeddings import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)

# Тестируем эмбеддинг
test_embedding = embeddings.embed_query("Привет мир")
print(f"Размерность эмбеддинга: {len(test_embedding)}")
```

### Доступные провайдеры эмбеддингов

```python
# OpenAI
from rlm_toolkit.embeddings import OpenAIEmbeddings
embeddings = OpenAIEmbeddings()

# Cohere
from rlm_toolkit.embeddings import CohereEmbeddings
embeddings = CohereEmbeddings()

# Локальный BGE
from rlm_toolkit.embeddings import BGEEmbeddings
embeddings = BGEEmbeddings(model_name="BAAI/bge-small-en-v1.5")

# Voyage AI
from rlm_toolkit.embeddings import VoyageEmbeddings
embeddings = VoyageEmbeddings()
```

## Шаг 4: Сохранение в векторную базу

```python
from rlm_toolkit.vectorstores import ChromaVectorStore

# Создаём и заполняем
vectorstore = ChromaVectorStore.from_documents(
    chunks,
    embeddings,
    collection_name="my-documents",
    persist_directory="./chroma_db"
)

print(f"Сохранено {vectorstore.count()} векторов")
```

### Другие векторные хранилища

```python
# Pinecone (управляемый)
from rlm_toolkit.vectorstores import PineconeVectorStore
vectorstore = PineconeVectorStore.from_documents(
    chunks, embeddings,
    index_name="my-index"
)

# Qdrant (self-hosted)
from rlm_toolkit.vectorstores import QdrantVectorStore
vectorstore = QdrantVectorStore.from_documents(
    chunks, embeddings,
    url="http://localhost:6333",
    collection_name="my-docs"
)

# PostgreSQL (pgvector)
from rlm_toolkit.vectorstores import PgVectorStore
vectorstore = PgVectorStore.from_documents(
    chunks, embeddings,
    connection_string="postgresql://user:pass@localhost/db"
)
```

## Шаг 5: Создание ретривера

```python
# Базовый ретривер
retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 5}  # Топ-5 результатов
)

# С порогом скора
retriever = vectorstore.as_retriever(
    search_type="similarity_score_threshold",
    search_kwargs={"score_threshold": 0.7, "k": 10}
)

# MMR (Maximum Marginal Relevance) для разнообразия
retriever = vectorstore.as_retriever(
    search_type="mmr",
    search_kwargs={"k": 5, "fetch_k": 20, "lambda_mult": 0.5}
)
```

## Шаг 6: Запросы с RLM

```python
from rlm_toolkit import RLM

# Создаём RLM с ретривером
rlm = RLM.from_openai(
    "gpt-4o",
    retriever=retriever
)

# Задаём вопросы
result = rlm.run("Каковы ключевые выводы отчёта?")
print(result.answer)

# Доступ к извлечённым документам
for doc in result.context_documents:
    print(f"Источник: {doc.metadata.get('source')}")
    print(f"Контент: {doc.content[:200]}...")
```

## Полное RAG-приложение

```python
# rag_app.py
from rlm_toolkit import RLM
from rlm_toolkit.loaders import PDFLoader, DirectoryLoader
from rlm_toolkit.splitters import RecursiveCharacterTextSplitter
from rlm_toolkit.embeddings import OpenAIEmbeddings
from rlm_toolkit.vectorstores import ChromaVectorStore
import os

class RAGApplication:
    def __init__(self, docs_directory: str, persist_dir: str = "./rag_db"):
        self.docs_directory = docs_directory
        self.persist_dir = persist_dir
        self.vectorstore = None
        self.rlm = None
    
    def index_documents(self):
        """Загружаем и индексируем все документы."""
        print("📄 Загрузка документов...")
        
        # Загружаем все PDF
        loader = DirectoryLoader(
            self.docs_directory,
            glob="**/*.pdf",
            loader_cls=PDFLoader,
            show_progress=True
        )
        documents = loader.load()
        print(f"   Загружено {len(documents)} документов")
        
        # Разбиваем на чанки
        print("✂️ Разбиение на чанки...")
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = splitter.split_documents(documents)
        print(f"   Создано {len(chunks)} чанков")
        
        # Создаём эмбеддинги и сохраняем
        print("🧮 Создание эмбеддингов...")
        embeddings = OpenAIEmbeddings()
        
        self.vectorstore = ChromaVectorStore.from_documents(
            chunks,
            embeddings,
            collection_name="rag-docs",
            persist_directory=self.persist_dir
        )
        print(f"   Сохранено {self.vectorstore.count()} векторов")
        
        return self
    
    def load_existing(self):
        """Загружаем существующее хранилище."""
        embeddings = OpenAIEmbeddings()
        self.vectorstore = ChromaVectorStore(
            collection_name="rag-docs",
            embedding_function=embeddings,
            persist_directory=self.persist_dir
        )
        print(f"📦 Загружено {self.vectorstore.count()} векторов")
        return self
    
    def setup_rlm(self):
        """Создаём RLM с ретривером."""
        retriever = self.vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 5}
        )
        
        self.rlm = RLM.from_openai(
            "gpt-4o",
            retriever=retriever,
            system_prompt="""Ты полезный ассистент, который отвечает на вопросы
            на основе предоставленных документов. Всегда указывай источники.
            Если не находишь релевантную информацию, скажи об этом."""
        )
        return self
    
    def query(self, question: str) -> str:
        """Запрос к RAG-системе."""
        result = self.rlm.run(question)
        return result.answer
    
    def interactive(self):
        """Запуск интерактивной сессии вопросов и ответов."""
        print("\n" + "="*50)
        print("📚 RAG-система готова!")
        print("   Введите 'выход' для завершения")
        print("="*50 + "\n")
        
        while True:
            question = input("❓ Вопрос: ")
            if question.lower() in ['выход', 'quit']:
                break
            
            answer = self.query(question)
            print(f"\n✅ Ответ: {answer}\n")

def main():
    # Проверяем, существует ли индекс
    if os.path.exists("./rag_db"):
        app = RAGApplication("./documents").load_existing()
    else:
        app = RAGApplication("./documents").index_documents()
    
    app.setup_rlm().interactive()

if __name__ == "__main__":
    main()
```

## Продвинутый режим: Использование InfiniRetri

Для очень больших документов (100K+ токенов) используйте InfiniRetri:

```python
from rlm_toolkit import RLM, RLMConfig

config = RLMConfig(
    use_infiniretri=True,
    infiniretri_threshold=100_000  # Порог токенов
)

rlm = RLM.from_openai(
    "gpt-4o",
    config=config,
    retriever=retriever
)

# InfiniRetri автоматически активируется для больших контекстов
result = rlm.run("Найди конкретный пункт об ответственности")
```

## Лучшие практики

!!! tip "Размер чанка"
    Выбирайте размер чанка в зависимости от контента:
    - Слишком маленький: теряется контекст
    - Слишком большой: извлекается нерелевантная информация

!!! tip "Модель эмбеддингов"
    Подбирайте модель под ваш случай:
    - `text-embedding-3-small`: Быстрая, подходит для большинства случаев
    - `text-embedding-3-large`: Выше качество, дороже

!!! tip "Стратегия извлечения"
    - Используйте MMR для разнообразия результатов
    - Используйте порог скора для фильтрации низкокачественных совпадений

!!! warning "Управление затратами"
    Эмбеддинг больших наборов документов может быть дорогим.
    Используйте параметр `batch_size` для контроля API-вызовов.

## Следующие шаги

- [Туториал 4: Агенты](04-agents.md)
- [Концепция: InfiniRetri](../concepts/infiniretri.md)
- [How-to: Загрузчики документов](../how-to/loaders.md)
