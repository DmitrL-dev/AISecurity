# Text Splitters

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **Интеллектуальное разбиение текста** для оптимального контекста

## Обзор

Text splitters делят большие документы на чанки для:
- RAG извлечения (семантические чанки)
- Управления контекстом (влезть в context window)
- Пайплайнов обработки (параллельная обработка)

## Быстрый старт

```python
from rlm_toolkit.splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

chunks = splitter.split_text(long_document)
print(f"Создано {len(chunks)} чанков")
```

## Сплиттеры

### RecursiveCharacterTextSplitter

Лучший универсальный сплиттер:

```python
from rlm_toolkit.splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,      # Целевой размер чанка
    chunk_overlap=200,    # Перекрытие между чанками
    separators=["\n\n", "\n", ". ", " ", ""]  # Иерархия
)

chunks = splitter.split_text(text)
```

### TokenTextSplitter

Для точного контроля токенов:

```python
from rlm_toolkit.splitters import TokenTextSplitter

splitter = TokenTextSplitter(
    chunk_size=500,       # В токенах
    chunk_overlap=50,
    model="gpt-4"         # Модель токенизатора
)
```

### MarkdownSplitter

Для markdown документов:

```python
from rlm_toolkit.splitters import MarkdownSplitter

splitter = MarkdownSplitter(
    chunk_size=1000,
    headers_to_split_on=[
        ("#", "H1"),
        ("##", "H2"),
        ("###", "H3")
    ]
)

chunks = splitter.split_text(markdown_doc)
# Чанки включают метаданные заголовков
```

### CodeSplitter

Для исходного кода:

```python
from rlm_toolkit.splitters import CodeSplitter

splitter = CodeSplitter(
    language="python",    # python, javascript, java, etc.
    chunk_size=1000,
    chunk_overlap=100
)

chunks = splitter.split_text(python_code)
# Разбивает по границам функций/классов
```

### SemanticSplitter

Для семантической связности:

```python
from rlm_toolkit.splitters import SemanticSplitter
from rlm_toolkit.embeddings import OpenAIEmbeddings

splitter = SemanticSplitter(
    embeddings=OpenAIEmbeddings(),
    breakpoint_threshold=0.5  # Порог схожести
)

chunks = splitter.split_text(text)
# Чанки семантически связные
```

## Примеры

### RAG Pipeline

```python
from rlm_toolkit.splitters import RecursiveCharacterTextSplitter
from rlm_toolkit.loaders import PDFLoader
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.embeddings import OpenAIEmbeddings

# Загрузка документа
loader = PDFLoader("manual.pdf")
pages = loader.load()

# Разбивка на чанки
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)
chunks = splitter.split_documents(pages)

# Сохранение в векторную базу
vectorstore = ChromaVectorStore.from_documents(
    chunks,
    OpenAIEmbeddings()
)
```

### Анализ кода

```python
from rlm_toolkit.splitters import CodeSplitter
from pathlib import Path

# Загрузка Python файлов
code_files = list(Path("./src").glob("**/*.py"))

splitter = CodeSplitter(language="python", chunk_size=2000)

all_chunks = []
for file_path in code_files:
    code = file_path.read_text()
    chunks = splitter.split_text(code)
    for chunk in chunks:
        chunk.metadata["source"] = str(file_path)
        all_chunks.append(chunk)

print(f"Всего чанков: {len(all_chunks)}")
```

### Смешанный документ

```python
from rlm_toolkit.splitters import (
    RecursiveCharacterTextSplitter,
    MarkdownSplitter,
    CodeSplitter
)

def smart_split(text, content_type):
    if content_type == "markdown":
        return MarkdownSplitter(chunk_size=1000).split_text(text)
    elif content_type == "code":
        return CodeSplitter(language="python").split_text(text)
    else:
        return RecursiveCharacterTextSplitter(chunk_size=1000).split_text(text)
```

## Рекомендации по размеру чанков

| Сценарий | Размер чанка | Перекрытие |
|----------|--------------|------------|
| Q&A / Поиск | 500-1000 | 50-100 |
| Суммаризация | 2000-4000 | 200-400 |
| Анализ | 1000-2000 | 100-200 |
| Код-ревью | 500-1500 | 50-150 |

## Связанное

- [Loaders](loaders.md)
- [RAG](rag.md)
- [Vector Stores](vectorstores.md)
