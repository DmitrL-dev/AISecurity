# Загрузчики документов

RLM-Toolkit поддерживает 135+ загрузчиков документов для импорта данных из различных источников.

## Категории загрузчиков

### Файловые загрузчики

| Загрузчик | Формат | Функции |
|-----------|--------|---------|
| **PDFLoader** | PDF | Извлечение текста, метаданные страниц |
| **DOCXLoader** | Word документы | Сохранение форматирования |
| **TextLoader** | Текст | UTF-8 кодировка |
| **MarkdownLoader** | Markdown | Парсинг frontmatter |
| **HTMLLoader** | HTML | Удаление тегов, извлечение текста |
| **CSVLoader** | CSV | Документы по строкам |
| **JSONLoader** | JSON | jq-подобные запросы путей |
| **ExcelLoader** | XLSX | Выбор листов |
| **PowerPointLoader** | PPTX | По слайдам |
| **EmailLoader** | EML, MSG | Метаданные заголовков |

### Веб загрузчики

| Загрузчик | Источник | Функции |
|-----------|----------|---------|
| **WebPageLoader** | URLs | HTML в текст |
| **SitemapLoader** | Sitemaps | Обход сайтов |
| **YouTubeLoader** | YouTube | Извлечение транскриптов |
| **GitHubLoader** | Репозитории | Issues, PR, код |
| **WikipediaLoader** | Wikipedia | Контент статей |
| **ArxivLoader** | arXiv | Метаданные статей |
| **SeleniumLoader** | Динамические страницы | JS рендеринг |

### Облачные загрузчики

| Загрузчик | Сервис | Функции |
|-----------|--------|---------|
| **S3Loader** | AWS S3 | Листинг бакетов |
| **GCSLoader** | Google Cloud | Доступ к blob |
| **AzureBlobLoader** | Azure Blob | Доступ к контейнерам |
| **GoogleDriveLoader** | Google Drive | Обход папок |
| **DropboxLoader** | Dropbox | Синхронизация файлов |

### API загрузчики

| Загрузчик | Сервис | Функции |
|-----------|--------|---------|
| **NotionLoader** | Notion | Базы данных, страницы |
| **SlackLoader** | Slack | История каналов |
| **JiraLoader** | Jira | Issues, комментарии |
| **ConfluenceLoader** | Confluence | Страницы, пространства |
| **HubSpotLoader** | HubSpot | CRM данные |

### Продвинутые загрузчики

| Загрузчик | Назначение | Функции |
|-----------|------------|---------|
| **UnstructuredLoader** | Сложные PDF | OCR, таблицы, изображения |
| **PDFParserLoader** | Мульти-backend | PyMuPDF, pdfplumber |
| **DocumentIntelligenceLoader** | Azure DI | Enterprise извлечение |

## Базовое использование

```python
from rlm_toolkit.loaders import PDFLoader, TextLoader, WebPageLoader

# Загрузка PDF
docs = PDFLoader("документ.pdf").load()

# Загрузка текстового файла
docs = TextLoader("заметки.txt").load()

# Загрузка веб-страницы
docs = WebPageLoader("https://example.com/article").load()

# Доступ к контенту
for doc in docs:
    print(f"Источник: {doc.metadata['source']}")
    print(f"Контент: {doc.content[:200]}...")
```

## Загрузка директории

```python
from rlm_toolkit.loaders import DirectoryLoader, PDFLoader

# Загрузка всех PDF из директории
loader = DirectoryLoader(
    "./documents",
    glob="**/*.pdf",
    loader_cls=PDFLoader,
    show_progress=True,
    recursive=True
)

docs = loader.load()
print(f"Загружено {len(docs)} документов")
```

## Ленивая загрузка

Для больших наборов документов:

```python
from rlm_toolkit.loaders import DirectoryLoader

loader = DirectoryLoader("./large_folder", glob="**/*.pdf")

# Ленивый итератор - не загружает всё сразу
for doc in loader.lazy_load():
    process(doc)
```

## Трансформации документов

### С метаданными

```python
from rlm_toolkit.loaders import PDFLoader

# Добавление пользовательских метаданных
loader = PDFLoader(
    "report.pdf",
    metadata_extractor=lambda path: {
        "year": 2024,
        "department": "Engineering"
    }
)

docs = loader.load()
```

### Очистка текста

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

## Продвинутая загрузка PDF

### Поддержка OCR

```python
from rlm_toolkit.loaders import UnstructuredLoader

# OCR для отсканированных PDF
loader = UnstructuredLoader(
    "scanned_document.pdf",
    ocr_enabled=True,
    ocr_languages=["en", "ru"]
)

docs = loader.load()
```

### Извлечение таблиц

```python
from rlm_toolkit.loaders import PDFParserLoader

# Извлечение таблиц как структурированных данных
loader = PDFParserLoader(
    "report_with_tables.pdf",
    extract_tables=True,
    table_format="markdown"  # или "html", "csv"
)

docs = loader.load()
```

### Извлечение изображений

```python
from rlm_toolkit.loaders import UnstructuredLoader

loader = UnstructuredLoader(
    "document_with_images.pdf",
    extract_images=True,
    image_output_dir="./extracted_images"
)

docs = loader.load()
```

## Веб-загрузка

### Базовая веб-загрузка

```python
from rlm_toolkit.loaders import WebPageLoader

# Одна страница
docs = WebPageLoader("https://example.com").load()

# Несколько страниц
docs = WebPageLoader([
    "https://example.com/page1",
    "https://example.com/page2"
]).load()
```

### Полный обход сайта

```python
from rlm_toolkit.loaders import SitemapLoader

loader = SitemapLoader(
    "https://example.com/sitemap.xml",
    filter_urls=lambda url: "/blog/" in url,
    max_pages=100
)

docs = loader.load()
```

### Динамические страницы

```python
from rlm_toolkit.loaders import SeleniumLoader

# Страницы с JavaScript
loader = SeleniumLoader(
    "https://spa-example.com",
    wait_time=5  # Ожидание рендеринга JS
)

docs = loader.load()
```

## API загрузчики

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

## Пользовательские загрузчики

```python
from rlm_toolkit.loaders import BaseLoader
from rlm_toolkit.types import Document

class MyCustomLoader(BaseLoader):
    def __init__(self, source: str):
        self.source = source
    
    def load(self) -> list[Document]:
        # Ваша логика загрузки
        content = self._fetch_data(self.source)
        
        return [Document(
            content=content,
            metadata={"source": self.source}
        )]
    
    def lazy_load(self):
        for item in self._fetch_items(self.source):
            yield Document(content=item, metadata={})
```

## Лучшие практики

!!! tip "Пакетная загрузка"
    Используйте `DirectoryLoader` для нескольких файлов:
    ```python
    loader = DirectoryLoader("./docs", glob="*.pdf")
    ```

!!! tip "Управление памятью"
    Используйте `lazy_load()` для больших наборов документов:
    ```python
    for doc in loader.lazy_load():
        process(doc)
    ```

!!! tip "Обработка ошибок"
    Обрабатывайте ошибки загрузки gracefully:
    ```python
    loader = DirectoryLoader(
        path, 
        silent_errors=True,  # Пропускать неудачные файлы
        on_error=lambda e: print(f"Ошибка: {e}")
    )
    ```

!!! tip "Кэширование"
    Кэшируйте загруженные документы:
    ```python
    from rlm_toolkit.loaders import CachedLoader
    
    loader = CachedLoader(
        PDFLoader("large.pdf"),
        cache_dir="./cache"
    )
    ```

## Связанное

- [Туториал: RAG Pipeline](../tutorials/03-rag.md)
- [How-to: Загрузка документов](../how-to/loaders.md)
- [Концепция: Векторные хранилища](./vectorstores.md)
