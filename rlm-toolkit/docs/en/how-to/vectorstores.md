# How-to: Configure Vector Stores

Recipes for setting up and using vector stores.

## Chroma (Development)

```python
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.embeddings import OpenAIEmbeddings

embeddings = OpenAIEmbeddings("text-embedding-3-small")

# In-memory
vs = ChromaVectorStore(
    embedding=embeddings,
    collection_name="temp"
)

# Persistent
vs = ChromaVectorStore(
    embedding=embeddings,
    collection_name="docs",
    persist_directory="./chroma_db"
)
```

## FAISS (Production)

```python
from rlm_toolkit.vectorstores import FAISSVectorStore

vs = FAISSVectorStore.from_documents(docs, embeddings)

# Save
vs.save_local("./faiss_index")

# Load
vs = FAISSVectorStore.load_local("./faiss_index", embeddings)
```

## Pinecone (Cloud)

```python
from rlm_toolkit.vectorstores import PineconeVectorStore

vs = PineconeVectorStore(
    index_name="my-index",
    embedding=embeddings,
    api_key="your-key",
    environment="us-west1-gcp"
)
```

## PGVector (PostgreSQL)

```python
from rlm_toolkit.vectorstores import PGVectorStore

vs = PGVectorStore(
    embedding=embeddings,
    connection_string="postgresql://user:pass@localhost/db",
    table_name="documents"
)
```

## Qdrant

```python
from rlm_toolkit.vectorstores import QdrantVectorStore

# Local
vs = QdrantVectorStore(
    embedding=embeddings,
    path="./qdrant_data",
    collection_name="docs"
)

# Server
vs = QdrantVectorStore(
    embedding=embeddings,
    url="http://localhost:6333",
    collection_name="docs"
)
```

## Add Documents

```python
vs.add_documents(documents)
```

## Search

```python
# Similarity search
results = vs.similarity_search("query", k=5)

# With scores
results = vs.similarity_search_with_score("query", k=5)

# With metadata filter
results = vs.similarity_search(
    "query",
    k=5,
    filter={"category": "tech"}
)
```

## MMR Search (Diversity)

```python
results = vs.max_marginal_relevance_search(
    "query",
    k=5,
    fetch_k=20,
    lambda_mult=0.5
)
```

## Delete Documents

```python
vs.delete(ids=["doc1", "doc2"])
vs.delete(filter={"category": "old"})
```

## Related

- [Concept: Vector Stores](../concepts/vectorstores.md)
- [Tutorial: RAG](../tutorials/03-rag.md)
