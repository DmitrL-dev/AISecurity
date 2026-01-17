# How-to: Configure Embeddings

Recipes for setting up embedding models.

## OpenAI Embeddings

```python
from rlm_toolkit.embeddings import OpenAIEmbeddings

# Default
embeddings = OpenAIEmbeddings("text-embedding-3-small")

# With options
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large",
    dimensions=1024,  # Reduce dimensions
    api_key="your-key"
)

# Embed text
vector = embeddings.embed_query("Hello world")
print(f"Dimensions: {len(vector)}")

# Embed documents
vectors = embeddings.embed_documents([
    "Document 1",
    "Document 2"
])
```

## Cohere Embeddings

```python
from rlm_toolkit.embeddings import CohereEmbeddings

embeddings = CohereEmbeddings(
    model="embed-english-v3.0",
    input_type="search_document"  # or "search_query"
)
```

## Local Embeddings (HuggingFace)

```python
from rlm_toolkit.embeddings import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    device="cuda"  # or "cpu"
)

# Multilingual
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
```

## Ollama Embeddings (Local)

```python
from rlm_toolkit.embeddings import OllamaEmbeddings

embeddings = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url="http://localhost:11434"
)
```

## Azure OpenAI Embeddings

```python
from rlm_toolkit.embeddings import AzureOpenAIEmbeddings

embeddings = AzureOpenAIEmbeddings(
    deployment_name="text-embedding-ada-002",
    api_key="your-azure-key",
    api_version="2024-02-15-preview",
    azure_endpoint="https://your-resource.openai.azure.com"
)
```

## Google Embeddings

```python
from rlm_toolkit.embeddings import GoogleEmbeddings

embeddings = GoogleEmbeddings(
    model="models/embedding-001",
    api_key="your-google-key"
)
```

## Voyage AI Embeddings

```python
from rlm_toolkit.embeddings import VoyageEmbeddings

embeddings = VoyageEmbeddings(
    model="voyage-large-2",
    api_key="your-voyage-key"
)
```

## Jina Embeddings

```python
from rlm_toolkit.embeddings import JinaEmbeddings

embeddings = JinaEmbeddings(
    model="jina-embeddings-v2-base-en",
    api_key="your-jina-key"
)
```

## Caching Embeddings

```python
from rlm_toolkit.embeddings import CachedEmbeddings

cached = CachedEmbeddings(
    embeddings=OpenAIEmbeddings("text-embedding-3-small"),
    cache_dir="./embedding_cache"
)

# First call computes, subsequent use cache
vector = cached.embed_query("Hello")
vector = cached.embed_query("Hello")  # From cache
```

## Comparison

| Model | Dimensions | Speed | Quality | Cost |
|-------|------------|-------|---------|------|
| text-embedding-3-small | 1536 | Fast | ⭐⭐⭐⭐ | $ |
| text-embedding-3-large | 3072 | Medium | ⭐⭐⭐⭐⭐ | $$ |
| all-MiniLM-L6-v2 | 384 | Fast | ⭐⭐⭐ | Free |
| nomic-embed-text | 768 | Fast | ⭐⭐⭐⭐ | Free |

## Related

- [Concept: Vector Stores](../concepts/vectorstores.md)
- [How-to: Vector Stores](./vectorstores.md)
