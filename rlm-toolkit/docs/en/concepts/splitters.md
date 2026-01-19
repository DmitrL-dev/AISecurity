# Text Splitters

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **Intelligent text chunking** for optimal context

## Overview

Text splitters divide large documents into chunks for:
- RAG retrieval (semantic chunks)
- Context management (fit in context window)
- Processing pipelines (parallel processing)

## Quick Start

```python
from rlm_toolkit.splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

chunks = splitter.split_text(long_document)
print(f"Created {len(chunks)} chunks")
```

## Splitters

### RecursiveCharacterTextSplitter

Best general-purpose splitter:

```python
from rlm_toolkit.splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,      # Target chunk size
    chunk_overlap=200,    # Overlap between chunks
    separators=["\n\n", "\n", ". ", " ", ""]  # Hierarchy
)

chunks = splitter.split_text(text)
```

### TokenTextSplitter

For precise token control:

```python
from rlm_toolkit.splitters import TokenTextSplitter

splitter = TokenTextSplitter(
    chunk_size=500,       # In tokens
    chunk_overlap=50,
    model="gpt-4"         # Tokenizer model
)
```

### MarkdownSplitter

For markdown documents:

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
# Chunks include header metadata
```

### CodeSplitter

For source code:

```python
from rlm_toolkit.splitters import CodeSplitter

splitter = CodeSplitter(
    language="python",    # python, javascript, java, etc.
    chunk_size=1000,
    chunk_overlap=100
)

chunks = splitter.split_text(python_code)
# Splits on function/class boundaries
```

### SemanticSplitter

For semantic coherence:

```python
from rlm_toolkit.splitters import SemanticSplitter
from rlm_toolkit.embeddings import OpenAIEmbeddings

splitter = SemanticSplitter(
    embeddings=OpenAIEmbeddings(),
    breakpoint_threshold=0.5  # Similarity threshold
)

chunks = splitter.split_text(text)
# Chunks are semantically coherent
```

## Examples

### RAG Pipeline

```python
from rlm_toolkit.splitters import RecursiveCharacterTextSplitter
from rlm_toolkit.loaders import PDFLoader
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.embeddings import OpenAIEmbeddings

# Load document
loader = PDFLoader("manual.pdf")
pages = loader.load()

# Split into chunks
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)
chunks = splitter.split_documents(pages)

# Store in vector database
vectorstore = ChromaVectorStore.from_documents(
    chunks,
    OpenAIEmbeddings()
)
```

### Code Analysis

```python
from rlm_toolkit.splitters import CodeSplitter
from pathlib import Path

# Load Python files
code_files = list(Path("./src").glob("**/*.py"))

splitter = CodeSplitter(language="python", chunk_size=2000)

all_chunks = []
for file_path in code_files:
    code = file_path.read_text()
    chunks = splitter.split_text(code)
    for chunk in chunks:
        chunk.metadata["source"] = str(file_path)
        all_chunks.append(chunk)

print(f"Total chunks: {len(all_chunks)}")
```

### Mixed Document

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

## Chunk Size Guidelines

| Use Case | Chunk Size | Overlap |
|----------|------------|---------|
| Q&A / Search | 500-1000 | 50-100 |
| Summarization | 2000-4000 | 200-400 |
| Analysis | 1000-2000 | 100-200 |
| Code review | 500-1500 | 50-150 |

## Related

- [Loaders](loaders.md)
- [RAG](rag.md)
- [Vector Stores](vectorstores.md)
