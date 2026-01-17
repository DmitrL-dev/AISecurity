# How-to: Load Documents

Recipes for loading documents from various sources.

## Load PDF Files

```python
from rlm_toolkit.loaders import PDFLoader

# Single PDF
docs = PDFLoader("document.pdf").load()

# With options
docs = PDFLoader(
    "document.pdf",
    extract_images=True,
    ocr_enabled=False
).load()
```

## Load Directory of Files

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

## Load Web Pages

```python
from rlm_toolkit.loaders import WebPageLoader

# Single URL
docs = WebPageLoader("https://example.com").load()

# Multiple URLs
docs = WebPageLoader([
    "https://example.com/page1",
    "https://example.com/page2"
]).load()
```

## Load with OCR (Scanned PDFs)

```python
from rlm_toolkit.loaders import UnstructuredLoader

loader = UnstructuredLoader(
    "scanned_document.pdf",
    ocr_enabled=True,
    ocr_languages=["en", "ru"]
)

docs = loader.load()
```

## Extract Tables from PDFs

```python
from rlm_toolkit.loaders import PDFParserLoader

loader = PDFParserLoader(
    "report.pdf",
    extract_tables=True,
    table_format="markdown"
)

docs = loader.load()
```

## Lazy Loading (Large Datasets)

```python
from rlm_toolkit.loaders import DirectoryLoader

loader = DirectoryLoader("./large_folder", glob="**/*.pdf")

for doc in loader.lazy_load():
    process(doc)
```

## Add Custom Metadata

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

## Load from Cloud Storage

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

## Load from APIs

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

## Related

- [Concept: Loaders](../concepts/loaders.md)
- [Tutorial: RAG](../tutorials/03-rag.md)
