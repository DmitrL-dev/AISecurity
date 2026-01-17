# How-to: InfiniRetri (Infinite Context)

Recipes for handling documents with 1M+ tokens.

## Enable InfiniRetri

```python
from rlm_toolkit import RLM, RLMConfig
from rlm_toolkit.retrieval import InfiniRetriConfig

config = RLMConfig(
    enable_infiniretri=True,
    infiniretri_config=InfiniRetriConfig(
        chunk_size=4000,
        chunk_overlap=200,
        top_k=5,
        attention_layer=-1,
        pooling="mean"
    ),
    infiniretri_threshold=50000  # Use for docs > 50K tokens
)

rlm = RLM.from_openai("gpt-4o", config=config)
```

## Process Long Documents

```python
from rlm_toolkit.loaders import PDFLoader

# Load 1000+ page document
docs = PDFLoader("massive_document.pdf").load()

# InfiniRetri automatically activates
response = rlm.run_with_docs(
    query="Summarize the key findings",
    documents=docs
)
```

## Configure Chunk Size

```python
config = InfiniRetriConfig(
    chunk_size=4000,      # Tokens per chunk (adjust for model)
    chunk_overlap=200,    # Overlap for context continuity
    top_k=5               # Top chunks to retrieve
)
```

## Custom Attention Layer

```python
config = InfiniRetriConfig(
    attention_layer=-1,   # Last layer (default)
    # attention_layer=12  # Specific layer
    pooling="mean"        # mean, max, or first
)
```

## Batch Processing

```python
from rlm_toolkit import RLM
from rlm_toolkit.retrieval import InfiniRetri

infini = InfiniRetri(
    llm=RLM.from_openai("gpt-4o"),
    config=InfiniRetriConfig(chunk_size=4000, top_k=5)
)

# Process multiple queries
queries = ["What is the revenue?", "Who are key stakeholders?"]
results = []

for query in queries:
    result = infini.run(
        query=query,
        documents=docs
    )
    results.append(result)
```

## Memory Optimization

```python
config = InfiniRetriConfig(
    chunk_size=2000,          # Smaller chunks = less memory
    top_k=3,                  # Fewer chunks = faster
    stream_chunks=True,       # Stream processing
    offload_to_disk=True,     # Disk offloading for huge docs
    offload_path="./cache"
)
```

## Compare vs Standard RAG

```python
# Standard RAG (may miss information)
standard_result = rag.run("Find the needle")  # ~85% accuracy

# InfiniRetri (attention-based)
infini_result = infini.run("Find the needle")  # 100% accuracy
```

## Use with Vector Store

```python
from rlm_toolkit.retrieval import HybridInfiniRetri

# Combine vector search + InfiniRetri
hybrid = HybridInfiniRetri(
    vectorstore=vectorstore,
    infini_config=InfiniRetriConfig(chunk_size=4000),
    vector_weight=0.3,
    attention_weight=0.7
)

result = hybrid.run(query, documents)
```

## Performance Tuning

| Document Size | Chunk Size | Top-K | Memory |
|---------------|------------|-------|--------|
| < 100K tokens | 4000 | 5 | ~4GB |
| 100K - 500K | 4000 | 3 | ~8GB |
| 500K - 1M | 2000 | 3 | ~16GB |
| > 1M tokens | 2000 | 2 | ~32GB |

## Related

- [Concept: InfiniRetri](../concepts/infiniretri.md)
- [Tutorial: InfiniRetri](../tutorials/06-infiniretri.md)
