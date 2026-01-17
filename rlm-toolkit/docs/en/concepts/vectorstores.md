# Vector Stores

RLM-Toolkit supports 41 vector stores for semantic search and retrieval.

## Supported Vector Stores

### Local/Embedded

| Store | Features | Use Case |
|-------|----------|----------|
| **Chroma** | Embedded, persistent | Development, small datasets |
| **FAISS** | CPU/GPU, fast | Production, large datasets |
| **LanceDB** | Embedded, columnar | Analytics + search |
| **Qdrant** | Embedded or server | Flexible deployment |
| **SQLite-VSS** | SQLite extension | Existing SQLite apps |

### Cloud/Managed

| Store | Features | Use Case |
|-------|----------|----------|
| **Pinecone** | Fully managed | Enterprise, scale |
| **Weaviate** | GraphQL, hybrid | Knowledge graphs |
| **Milvus** | Distributed | Massive scale |
| **Zilliz** | Managed Milvus | Cloud Milvus |
| **Vespa** | Yahoo's engine | Search + ML |

### Database Extensions

| Store | Database | Features |
|-------|----------|----------|
| **PGVector** | PostgreSQL | SQL + vectors |
| **Supabase Vector** | Supabase | Auth + vectors |
| **MongoDB Atlas** | MongoDB | Document + vectors |
| **Redis Stack** | Redis | Cache + vectors |
| **Elasticsearch** | Elasticsearch | Full-text + vectors |
| **OpenSearch** | OpenSearch | AWS compatible |
| **SingleStore** | SingleStore | OLTP + vectors |
| **ClickHouse** | ClickHouse | Analytics + vectors |

## Basic Usage

### Creating a Vector Store

```python
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.embeddings import OpenAIEmbeddings
from rlm_toolkit.loaders import PDFLoader

# Load documents
docs = PDFLoader("document.pdf").load()

# Create embeddings
embeddings = OpenAIEmbeddings("text-embedding-3-small")

# Create vector store
vectorstore = ChromaVectorStore.from_documents(
    documents=docs,
    embedding=embeddings,
    collection_name="my_documents",
    persist_directory="./chroma_db"
)
```

### Search

```python
# Similarity search
results = vectorstore.similarity_search(
    query="What is machine learning?",
    k=5
)

for doc in results:
    print(f"Score: {doc.metadata.get('score', 'N/A')}")
    print(f"Content: {doc.content[:200]}...")
```

### With Scores

```python
# Get similarity scores
results = vectorstore.similarity_search_with_score(
    query="What is machine learning?",
    k=5
)

for doc, score in results:
    print(f"Score: {score:.4f}")
    print(f"Content: {doc.content[:200]}...")
```

## Vector Store Types

### Chroma (Recommended for Development)

```python
from rlm_toolkit.vectorstores import ChromaVectorStore

# Ephemeral (in-memory)
vs = ChromaVectorStore(
    embedding=embeddings,
    collection_name="temp"
)

# Persistent
vs = ChromaVectorStore(
    embedding=embeddings,
    collection_name="persistent",
    persist_directory="./chroma_db"
)
```

### FAISS (Recommended for Production)

```python
from rlm_toolkit.vectorstores import FAISSVectorStore

# Create from documents
vs = FAISSVectorStore.from_documents(
    documents=docs,
    embedding=embeddings
)

# Save and load
vs.save_local("./faiss_index")
vs = FAISSVectorStore.load_local(
    "./faiss_index", 
    embeddings
)
```

### Pinecone (Cloud)

```python
from rlm_toolkit.vectorstores import PineconeVectorStore

vs = PineconeVectorStore(
    index_name="my-index",
    embedding=embeddings,
    api_key="your-pinecone-key",
    environment="us-west1-gcp"
)
```

### PGVector (PostgreSQL)

```python
from rlm_toolkit.vectorstores import PGVectorStore

vs = PGVectorStore(
    embedding=embeddings,
    connection_string="postgresql://user:pass@localhost/db",
    table_name="documents"
)
```

### Qdrant

```python
from rlm_toolkit.vectorstores import QdrantVectorStore

# Local
vs = QdrantVectorStore(
    embedding=embeddings,
    path="./qdrant_data",
    collection_name="documents"
)

# Server
vs = QdrantVectorStore(
    embedding=embeddings,
    url="http://localhost:6333",
    collection_name="documents"
)
```

## Advanced Features

### Metadata Filtering

```python
# Filter by metadata
results = vectorstore.similarity_search(
    query="machine learning",
    k=5,
    filter={"category": "technology", "year": {"$gte": 2023}}
)
```

### Hybrid Search

```python
from rlm_toolkit.vectorstores import WeaviateVectorStore

vs = WeaviateVectorStore(
    embedding=embeddings,
    url="http://localhost:8080"
)

# Combine semantic + keyword search
results = vs.hybrid_search(
    query="machine learning neural networks",
    alpha=0.5,  # Balance: 0=keyword, 1=semantic
    k=5
)
```

### MMR (Maximal Marginal Relevance)

```python
# Diverse results (reduces redundancy)
results = vectorstore.max_marginal_relevance_search(
    query="machine learning",
    k=5,
    fetch_k=20,  # Fetch more, then diversify
    lambda_mult=0.5  # Diversity factor
)
```

### Batch Operations

```python
# Add documents in batches
vectorstore.add_documents(
    documents=new_docs,
    batch_size=100
)

# Delete by IDs
vectorstore.delete(ids=["doc1", "doc2"])

# Delete by filter
vectorstore.delete(filter={"category": "old"})
```

## RAG Integration

```python
from rlm_toolkit import RLM
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.retrievers import VectorStoreRetriever

# Create retriever from vectorstore
retriever = VectorStoreRetriever(
    vectorstore=vectorstore,
    search_type="similarity",
    search_kwargs={"k": 5}
)

# Use with RLM
rlm = RLM.from_openai("gpt-4o")
rlm.set_retriever(retriever)

# Now queries use RAG automatically
response = rlm.run("What does the document say about X?")
```

## Comparison

| Store | Speed | Scale | Persistence | Cloud | Cost |
|-------|-------|-------|-------------|-------|------|
| Chroma | ⭐⭐⭐ | Small-Med | ✅ | ❌ | Free |
| FAISS | ⭐⭐⭐⭐⭐ | Large | ✅ | ❌ | Free |
| Pinecone | ⭐⭐⭐⭐ | Massive | ✅ | ✅ | $$ |
| Qdrant | ⭐⭐⭐⭐ | Large | ✅ | ✅ | Free/$ |
| PGVector | ⭐⭐⭐ | Med-Large | ✅ | ✅ | $ |
| Weaviate | ⭐⭐⭐⭐ | Large | ✅ | ✅ | Free/$ |

## Best Practices

!!! tip "Development vs Production"
    - **Development**: Use Chroma (embedded, easy setup)
    - **Production**: Use FAISS, Qdrant, or Pinecone

!!! tip "Index Size"
    - < 100K vectors: Chroma, SQLite-VSS
    - 100K - 10M: FAISS, Qdrant
    - > 10M: Pinecone, Milvus, Weaviate

!!! tip "Hybrid Search"
    Combine semantic + keyword for better recall:
    ```python
    results = vs.hybrid_search(query, alpha=0.7)
    ```

!!! tip "Metadata Strategy"
    Store useful metadata for filtering:
    ```python
    doc.metadata = {
        "source": "report.pdf",
        "page": 5,
        "category": "finance",
        "date": "2024-01-15"
    }
    ```

## Related

- [Tutorial: RAG Pipeline](../tutorials/03-rag.md)
- [Concept: Loaders](./loaders.md)
- [Tutorial: InfiniRetri](../tutorials/06-infiniretri.md)
