# How-to: Разделители текста

Рецепты разбиения документов на чанки.

## Рекурсивный разделитель (рекомендуемый)

```python
from rlm_toolkit.splitters import RecursiveTextSplitter

splitter = RecursiveTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", " ", ""]
)

chunks = splitter.split_documents(docs)
```

## Токен-основанный разделитель

```python
from rlm_toolkit.splitters import TokenTextSplitter

splitter = TokenTextSplitter(
    chunk_size=500,     # токенов
    chunk_overlap=50,
    model="gpt-4o"      # для токенизации
)
```

## Markdown разделитель

```python
from rlm_toolkit.splitters import MarkdownSplitter

splitter = MarkdownSplitter(
    chunk_size=1000,
    headers_to_split_on=["#", "##", "###"]
)

# Сохраняет структуру markdown
chunks = splitter.split_documents(markdown_docs)
```

## Разделитель кода

```python
from rlm_toolkit.splitters import CodeSplitter

splitter = CodeSplitter(
    chunk_size=500,
    language="python"  # или "javascript", "java" и т.д.
)

chunks = splitter.split_documents(code_docs)
```

## HTML разделитель

```python
from rlm_toolkit.splitters import HTMLSplitter

splitter = HTMLSplitter(
    chunk_size=1000,
    headers_to_split_on=["h1", "h2", "h3"]
)
```

## Семантический разделитель

```python
from rlm_toolkit.splitters import SemanticSplitter
from rlm_toolkit.embeddings import OpenAIEmbeddings

splitter = SemanticSplitter(
    embeddings=OpenAIEmbeddings(),
    breakpoint_threshold_type="percentile",
    breakpoint_threshold=95
)

# Разделяет на основе семантической схожести
chunks = splitter.split_documents(docs)
```

## Предложения разделитель

```python
from rlm_toolkit.splitters import SentenceSplitter

splitter = SentenceSplitter(
    chunk_size=1000,
    chunk_overlap=0  # Без перекрытия для предложений
)
```

## Символьный разделитель

```python
from rlm_toolkit.splitters import CharacterTextSplitter

splitter = CharacterTextSplitter(
    separator="\n\n",
    chunk_size=1000,
    chunk_overlap=200
)
```

## Разбиение с метаданными

```python
splitter = RecursiveTextSplitter(chunk_size=1000)
chunks = splitter.split_documents(docs)

# Каждый чанк имеет метаданные
for chunk in chunks:
    print(chunk.metadata)  # {"source": "doc.pdf", "chunk_index": 0}
```

## Пользовательский разделитель

```python
from rlm_toolkit.splitters import BaseSplitter

class CustomSplitter(BaseSplitter):
    def split_text(self, text: str) -> list[str]:
        # Ваша логика разделения
        return text.split("===")
```

## Лучшие практики

| Применение | Рекомендуемый разделитель | Размер чанка |
|------------|--------------------------|--------------|
| Общий текст | RecursiveTextSplitter | 500-1000 |
| LLM контекст | TokenTextSplitter | 500 токенов |
| Markdown документы | MarkdownSplitter | 1000 |
| Исходный код | CodeSplitter | 500 |
| Семантический поиск | SemanticSplitter | авто |

## Связанное

- [How-to: Загрузчики](./loaders.md)
- [How-to: RAG](./rag.md)
