# How-to: Загрузка документов

Рецепты загрузки документов из различных источников.

## Загрузка PDF файлов

```python
from rlm_toolkit.loaders import PDFLoader

# Один PDF
docs = PDFLoader("document.pdf").load()

# С опциями
docs = PDFLoader(
    "document.pdf",
    extract_images=True,
    ocr_enabled=False
).load()
```

## Загрузка директории файлов

```python
from rlm_toolkit.loaders import DirectoryLoader, PDFLoader

loader = DirectoryLoader(
    path="./documents",
    glob="**/*.pdf",
    loader_cls=PDFLoader,
    show_progress=True,
    recursive=True
)

docs = loader.load()
```

## Загрузка веб-страниц

```python
from rlm_toolkit.loaders import WebPageLoader

# Один URL
docs = WebPageLoader("https://example.com").load()

# Несколько URL
docs = WebPageLoader([
    "https://example.com/page1",
    "https://example.com/page2"
]).load()
```

## Загрузка с OCR (сканированные PDF)

```python
from rlm_toolkit.loaders import UnstructuredLoader

loader = UnstructuredLoader(
    "scanned_document.pdf",
    ocr_enabled=True,
    ocr_languages=["en", "ru"]
)

docs = loader.load()
```

## Извлечение таблиц из PDF

```python
from rlm_toolkit.loaders import PDFParserLoader

loader = PDFParserLoader(
    "report.pdf",
    extract_tables=True,
    table_format="markdown"
)

docs = loader.load()
```

## Ленивая загрузка (большие датасеты)

```python
from rlm_toolkit.loaders import DirectoryLoader

loader = DirectoryLoader("./large_folder", glob="**/*.pdf")

for doc in loader.lazy_load():
    process(doc)
```

## Добавление пользовательских метаданных

```python
from rlm_toolkit.loaders import PDFLoader

loader = PDFLoader(
    "report.pdf",
    metadata_extractor=lambda path: {
        "department": "Engineering",
        "year": 2024
    }
)
```

## Загрузка из облачного хранилища

```python
from rlm_toolkit.loaders import S3Loader, GCSLoader

# AWS S3
docs = S3Loader(
    bucket="my-bucket",
    prefix="documents/",
    aws_access_key_id="...",
    aws_secret_access_key="..."
).load()

# Google Cloud Storage
docs = GCSLoader(
    bucket="my-bucket",
    prefix="documents/"
).load()
```

## Загрузка из API

```python
from rlm_toolkit.loaders import NotionLoader, GitHubLoader

# Notion
docs = NotionLoader(
    database_id="...",
    api_key="..."
).load()

# GitHub
docs = GitHubLoader(
    repo="owner/repo",
    file_filter=lambda f: f.endswith(".py")
).load()
```

## Связанное

- [Концепция: Загрузчики](../concepts/loaders.md)
- [Туториал: RAG](../tutorials/03-rag.md)
