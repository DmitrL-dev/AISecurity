# Embeddings

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **Text embeddings** from 15+ providers

## Overview

RLM-Toolkit supports multiple embedding providers:
- OpenAI (text-embedding-3-large, ada-002)
- Cohere (embed-english-v3.0)
- Google (text-embedding-004)
- HuggingFace (BGE, E5, BAAI)
- Jina AI, Voyage, Mistral
- Local models via Ollama/Sentence Transformers

## Quick Start

```python
from rlm_toolkit.embeddings import OpenAIEmbeddings

# Create embedder
embedder = OpenAIEmbeddings(model="text-embedding-3-small")

# Embed text
vector = embedder.embed_query("Hello, world!")
print(f"Dimensions: {len(vector)}")  # 1536

# Embed multiple texts
vectors = embedder.embed_documents([
    "First document",
    "Second document",
    "Third document"
])
```

## Providers

### OpenAI

```python
from rlm_toolkit.embeddings import OpenAIEmbeddings

# Default (text-embedding-3-small)
embedder = OpenAIEmbeddings()

# High-dimensional
embedder = OpenAIEmbeddings(
    model="text-embedding-3-large",
    dimensions=3072  # or 256, 1024 for lower cost
)
```

### Cohere

```python
from rlm_toolkit.embeddings import CohereEmbeddings

embedder = CohereEmbeddings(
    model="embed-english-v3.0",
    input_type="search_document"  # or "search_query"
)
```

### HuggingFace (BGE, E5)

```python
from rlm_toolkit.embeddings import HuggingFaceEmbeddings

# BGE (best open-source)
embedder = HuggingFaceEmbeddings(
    model_name="BAAI/bge-large-en-v1.5"
)

# E5
embedder = HuggingFaceEmbeddings(
    model_name="intfloat/e5-large-v2"
)
```

### Ollama (Local)

```python
from rlm_toolkit.embeddings import OllamaEmbeddings

# Free, runs locally
embedder = OllamaEmbeddings(model="nomic-embed-text")
```

### Jina AI

```python
from rlm_toolkit.embeddings import JinaEmbeddings

embedder = JinaEmbeddings(
    model="jina-embeddings-v2-base-en",
    api_key="..."
)
```

### Voyage AI

```python
from rlm_toolkit.embeddings import VoyageEmbeddings

embedder = VoyageEmbeddings(
    model="voyage-large-2",
    api_key="..."
)
```

## Use Cases

### RAG Pipeline

```python
from rlm_toolkit.embeddings import OpenAIEmbeddings
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.loaders import PDFLoader

# Load documents
docs = PDFLoader("guide.pdf").load()

# Create embeddings and store
embedder = OpenAIEmbeddings()
vectorstore = ChromaVectorStore.from_documents(docs, embedder)

# Search
results = vectorstore.similarity_search("How to configure?", k=5)
```

### Semantic Search

```python
import numpy as np
from rlm_toolkit.embeddings import OpenAIEmbeddings

embedder = OpenAIEmbeddings()

# Corpus
documents = [
    "Python is a programming language",
    "France is a country in Europe",
    "Machine learning is a branch of AI"
]
doc_vectors = embedder.embed_documents(documents)

# Query
query = "What is Python?"
query_vector = embedder.embed_query(query)

# Find most similar
similarities = [
    np.dot(query_vector, doc_vec)
    for doc_vec in doc_vectors
]
best_idx = np.argmax(similarities)
print(f"Best match: {documents[best_idx]}")
```

### Caching Embeddings

```python
from rlm_toolkit.embeddings import OpenAIEmbeddings, CachedEmbeddings

# Wrap with cache
base = OpenAIEmbeddings()
embedder = CachedEmbeddings(
    base_embeddings=base,
    cache_path="./.embedding_cache"
)

# First call: computes and caches
v1 = embedder.embed_query("Hello")

# Second call: returns from cache (instant, free)
v2 = embedder.embed_query("Hello")
```

### Batch Processing

```python
from rlm_toolkit.embeddings import OpenAIEmbeddings

embedder = OpenAIEmbeddings(
    batch_size=100,  # Process 100 at a time
    show_progress=True
)

# Large dataset
texts = load_million_documents()

# Efficient batched processing
all_vectors = embedder.embed_documents(texts)
print(f"Embedded {len(all_vectors)} documents")
```

## Cost Comparison

| Provider | Model | Cost/1M tokens | Dimensions |
|----------|-------|----------------|------------|
| OpenAI | text-embedding-3-small | $0.02 | 1536 |
| OpenAI | text-embedding-3-large | $0.13 | 3072 |
| Cohere | embed-english-v3.0 | $0.10 | 1024 |
| Voyage | voyage-large-2 | $0.12 | 1536 |
| Ollama | nomic-embed-text | Free | 768 |
| HuggingFace | bge-large | Free | 1024 |

## Related

- [Vector Stores](vectorstores.md)
- [RAG Pipeline](rag.md)
- [Tutorial: RAG](../tutorials/03-rag.md)
