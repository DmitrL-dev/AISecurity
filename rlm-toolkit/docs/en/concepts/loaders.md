# Document Loaders

RLM-Toolkit supports 135+ document loaders for ingesting data from various sources.

## Loader Categories

### File Loaders

| Loader | Format | Features |
|--------|--------|----------|
| **PDFLoader** | PDF | Text extraction, page metadata |
| **DOCXLoader** | Word documents | Formatting preservation |
| **TextLoader** | Plain text | UTF-8 encoding |
| **MarkdownLoader** | Markdown | Frontmatter parsing |
| **HTMLLoader** | HTML | Tag stripping, text extraction |
| **CSVLoader** | CSV | Row-by-row documents |
| **JSONLoader** | JSON | jq-like path queries |
| **ExcelLoader** | XLSX | Sheet selection |
| **PowerPointLoader** | PPTX | Slide-by-slide |
| **EmailLoader** | EML, MSG | Header metadata |

### Web Loaders

| Loader | Source | Features |
|--------|--------|----------|
| **WebPageLoader** | URLs | HTML to text |
| **SitemapLoader** | Sitemaps | Crawl entire sites |
| **YouTubeLoader** | YouTube | Transcript extraction |
| **GitHubLoader** | Repositories | Issue, PR, code |
| **WikipediaLoader** | Wikipedia | Article content |
| **ArxivLoader** | arXiv | Paper metadata |
| **SeleniumLoader** | Dynamic pages | JS rendering |

### Cloud Loaders

| Loader | Service | Features |
|--------|---------|----------|
| **S3Loader** | AWS S3 | Bucket listing |
| **GCSLoader** | Google Cloud | Blob access |
| **AzureBlobLoader** | Azure Blob | Container access |
| **GoogleDriveLoader** | Google Drive | Folder traversal |
| **DropboxLoader** | Dropbox | File sync |

### API Loaders

| Loader | Service | Features |
|--------|---------|----------|
| **NotionLoader** | Notion | Database, pages |
| **SlackLoader** | Slack | Channel history |
| **JiraLoader** | Jira | Issues, comments |
| **ConfluenceLoader** | Confluence | Pages, spaces |
| **HubSpotLoader** | HubSpot | CRM data |

### Advanced Loaders

| Loader | Purpose | Features |
|--------|---------|----------|
| **UnstructuredLoader** | Complex PDFs | OCR, tables, images |
| **PDFParserLoader** | Multi-backend | PyMuPDF, pdfplumber |
| **DocumentIntelligenceLoader** | Azure DI | Enterprise extraction |

## Basic Usage

```python
from rlm_toolkit.loaders import PDFLoader, TextLoader, WebPageLoader

# Load a PDF
docs = PDFLoader("document.pdf").load()

# Load text file
docs = TextLoader("notes.txt").load()

# Load web page
docs = WebPageLoader("https://example.com/article").load()

# Access content
for doc in docs:
    print(f"Source: {doc.metadata['source']}")
    print(f"Content: {doc.content[:200]}...")
```

## Directory Loading

```python
from rlm_toolkit.loaders import DirectoryLoader, PDFLoader

# Load all PDFs from directory
loader = DirectoryLoader(
    "./documents",
    glob="**/*.pdf",
    loader_cls=PDFLoader,
    show_progress=True,
    recursive=True
)

docs = loader.load()
print(f"Loaded {len(docs)} documents")
```

## Lazy Loading

For large document sets:

```python
from rlm_toolkit.loaders import DirectoryLoader

loader = DirectoryLoader("./large_folder", glob="**/*.pdf")

# Lazy iterator - doesn't load all at once
for doc in loader.lazy_load():
    process(doc)
```

## Document Transformations

### With Metadata

```python
from rlm_toolkit.loaders import PDFLoader

# Add custom metadata
loader = PDFLoader(
    "report.pdf",
    metadata_extractor=lambda path: {
        "year": 2024,
        "department": "Engineering"
    }
)

docs = loader.load()
```

### Text Cleaning

```python
from rlm_toolkit.loaders import PDFLoader
from rlm_toolkit.loaders.transforms import CleanText

loader = PDFLoader("messy.pdf")
loader.add_transform(CleanText(
    remove_extra_whitespace=True,
    remove_urls=False,
    lowercase=False
))

docs = loader.load()
```

## Advanced PDF Loading

### OCR Support

```python
from rlm_toolkit.loaders import UnstructuredLoader

# OCR for scanned PDFs
loader = UnstructuredLoader(
    "scanned_document.pdf",
    ocr_enabled=True,
    ocr_languages=["en", "ru"]
)

docs = loader.load()
```

### Table Extraction

```python
from rlm_toolkit.loaders import PDFParserLoader

# Extract tables as structured data
loader = PDFParserLoader(
    "report_with_tables.pdf",
    extract_tables=True,
    table_format="markdown"  # or "html", "csv"
)

docs = loader.load()
```

### Image Extraction

```python
from rlm_toolkit.loaders import UnstructuredLoader

loader = UnstructuredLoader(
    "document_with_images.pdf",
    extract_images=True,
    image_output_dir="./extracted_images"
)

docs = loader.load()
```

## Web Loading

### Basic Web

```python
from rlm_toolkit.loaders import WebPageLoader

# Single page
docs = WebPageLoader("https://example.com").load()

# Multiple pages
docs = WebPageLoader([
    "https://example.com/page1",
    "https://example.com/page2"
]).load()
```

### Full Site Crawl

```python
from rlm_toolkit.loaders import SitemapLoader

loader = SitemapLoader(
    "https://example.com/sitemap.xml",
    filter_urls=lambda url: "/blog/" in url,
    max_pages=100
)

docs = loader.load()
```

### Dynamic Pages

```python
from rlm_toolkit.loaders import SeleniumLoader

# Pages with JavaScript
loader = SeleniumLoader(
    "https://spa-example.com",
    wait_time=5  # Wait for JS to render
)

docs = loader.load()
```

## API Loaders

### GitHub

```python
from rlm_toolkit.loaders import GitHubLoader

loader = GitHubLoader(
    repo="owner/repo",
    file_filter=lambda f: f.endswith(".py"),
    branch="main"
)

docs = loader.load()
```

### Notion

```python
from rlm_toolkit.loaders import NotionLoader

loader = NotionLoader(
    database_id="your-database-id",
    api_key="your-notion-key"
)

docs = loader.load()
```

## Custom Loaders

```python
from rlm_toolkit.loaders import BaseLoader
from rlm_toolkit.types import Document

class MyCustomLoader(BaseLoader):
    def __init__(self, source: str):
        self.source = source
    
    def load(self) -> list[Document]:
        # Your loading logic
        content = self._fetch_data(self.source)
        
        return [Document(
            content=content,
            metadata={"source": self.source}
        )]
    
    def lazy_load(self):
        for item in self._fetch_items(self.source):
            yield Document(content=item, metadata={})
```

## Best Practices

!!! tip "Batch Loading"
    Use `DirectoryLoader` for multiple files:
    ```python
    loader = DirectoryLoader("./docs", glob="*.pdf")
    ```

!!! tip "Memory Management"
    Use `lazy_load()` for large document sets:
    ```python
    for doc in loader.lazy_load():
        process(doc)
    ```

!!! tip "Error Handling"
    Handle loading errors gracefully:
    ```python
    loader = DirectoryLoader(
        path, 
        silent_errors=True,  # Skip failed files
        on_error=lambda e: print(f"Error: {e}")
    )
    ```

!!! tip "Caching"
    Cache loaded documents:
    ```python
    from rlm_toolkit.loaders import CachedLoader
    
    loader = CachedLoader(
        PDFLoader("large.pdf"),
        cache_dir="./cache"
    )
    ```

## Related

- [Tutorial: RAG Pipeline](../tutorials/03-rag.md)
- [How-to: Document Loading](../how-to/loaders.md)
- [Concept: Vector Stores](./vectorstores.md)
