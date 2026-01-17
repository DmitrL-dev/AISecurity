# How-to: Text Splitters

Recipes for splitting documents into chunks.

## Recursive Text Splitter (Recommended)

```python
from rlm_toolkit.splitters import RecursiveTextSplitter

splitter = RecursiveTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", " ", ""]
)

chunks = splitter.split_documents(docs)
```

## Token-Based Splitter

```python
from rlm_toolkit.splitters import TokenTextSplitter

splitter = TokenTextSplitter(
    chunk_size=500,     # tokens
    chunk_overlap=50,
    model="gpt-4o"      # for tokenization
)
```

## Markdown Splitter

```python
from rlm_toolkit.splitters import MarkdownSplitter

splitter = MarkdownSplitter(
    chunk_size=1000,
    headers_to_split_on=["#", "##", "###"]
)

# Preserves markdown structure
chunks = splitter.split_documents(markdown_docs)
```

## Code Splitter

```python
from rlm_toolkit.splitters import CodeSplitter

splitter = CodeSplitter(
    chunk_size=500,
    language="python"  # or "javascript", "java", etc.
)

chunks = splitter.split_documents(code_docs)
```

## HTML Splitter

```python
from rlm_toolkit.splitters import HTMLSplitter

splitter = HTMLSplitter(
    chunk_size=1000,
    headers_to_split_on=["h1", "h2", "h3"]
)
```

## Semantic Splitter

```python
from rlm_toolkit.splitters import SemanticSplitter
from rlm_toolkit.embeddings import OpenAIEmbeddings

splitter = SemanticSplitter(
    embeddings=OpenAIEmbeddings(),
    breakpoint_threshold_type="percentile",
    breakpoint_threshold=95
)

# Splits based on semantic similarity
chunks = splitter.split_documents(docs)
```

## Sentence Splitter

```python
from rlm_toolkit.splitters import SentenceSplitter

splitter = SentenceSplitter(
    chunk_size=1000,
    chunk_overlap=0  # No overlap for sentences
)
```

## Character Splitter

```python
from rlm_toolkit.splitters import CharacterTextSplitter

splitter = CharacterTextSplitter(
    separator="\n\n",
    chunk_size=1000,
    chunk_overlap=200
)
```

## Split with Metadata

```python
splitter = RecursiveTextSplitter(chunk_size=1000)
chunks = splitter.split_documents(docs)

# Each chunk has metadata
for chunk in chunks:
    print(chunk.metadata)  # {"source": "doc.pdf", "chunk_index": 0}
```

## Custom Splitter

```python
from rlm_toolkit.splitters import BaseSplitter

class CustomSplitter(BaseSplitter):
    def split_text(self, text: str) -> list[str]:
        # Your splitting logic
        return text.split("===")
```

## Best Practices

| Use Case | Recommended Splitter | Chunk Size |
|----------|---------------------|------------|
| General text | RecursiveTextSplitter | 500-1000 |
| LLM context | TokenTextSplitter | 500 tokens |
| Markdown docs | MarkdownSplitter | 1000 |
| Source code | CodeSplitter | 500 |
| Semantic search | SemanticSplitter | auto |

## Related

- [How-to: Loaders](./loaders.md)
- [How-to: RAG](./rag.md)
