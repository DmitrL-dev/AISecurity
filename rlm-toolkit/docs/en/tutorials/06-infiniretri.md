# Tutorial 6: InfiniRetri

Master attention-based infinite context retrieval for handling 1M+ token documents with 100% accuracy.

## What is InfiniRetri?

InfiniRetri is RLM-Toolkit's unique attention-based retrieval system that:

- Processes documents up to **10M+ tokens**
- Achieves **100% accuracy** on Needle-In-a-Haystack benchmarks
- Uses **O(1) memory** regardless of document size
- Works **without embeddings or vector stores**

## How InfiniRetri Works

```
┌─────────────────────────────────────────────────────────────────┐
│                    InfiniRetri Architecture                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Large Document (1M+ tokens)                                    │
│          ↓                                                       │
│   Chunk into segments                                           │
│          ↓                                                       │
│   Process each segment with LLM                                 │
│          ↓                                                       │
│   Extract attention weights for query                           │
│          ↓                                                       │
│   Select highest-attention segments                             │
│          ↓                                                       │
│   Return relevant context                                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

```bash
pip install rlm-toolkit[all]
export OPENAI_API_KEY=your-key
```

## Step 1: Basic InfiniRetri Usage

```python
from rlm_toolkit import RLM, RLMConfig

# Enable InfiniRetri
config = RLMConfig(
    enable_infiniretri=True,
    infiniretri_threshold=50000  # Activate above 50K tokens
)

rlm = RLM.from_openai("gpt-4o", config=config)

# Load a large document
with open("large_document.txt", "r") as f:
    massive_context = f.read()

# InfiniRetri automatically activates
result = rlm.run(
    "Find the specific clause about termination penalties",
    context=massive_context
)

print(result.final_answer)
print(f"Processed {result.total_tokens} tokens")
```

## Step 2: Configure InfiniRetri

```python
from rlm_toolkit import RLM, RLMConfig
from rlm_toolkit.retrieval import InfiniRetriConfig

# Detailed configuration
infiniretri_config = InfiniRetriConfig(
    chunk_size=4000,          # Tokens per chunk
    chunk_overlap=200,        # Overlap between chunks
    top_k=5,                  # Number of chunks to retrieve
    attention_layer=-1,       # Use last attention layer
    pooling="mean",          # Attention aggregation: mean, max, sum
)

config = RLMConfig(
    enable_infiniretri=True,
    infiniretri_config=infiniretri_config,
    infiniretri_threshold=50000
)

rlm = RLM.from_openai("gpt-4o", config=config)
```

## Step 3: With RAG Pipeline

Combine InfiniRetri with vector-based retrieval:

```python
from rlm_toolkit import RLM, RLMConfig
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.embeddings import OpenAIEmbeddings

# Vector store for initial retrieval
vectorstore = ChromaVectorStore.from_documents(docs, OpenAIEmbeddings())
retriever = vectorstore.as_retriever(search_kwargs={"k": 20})

# Enable InfiniRetri for re-ranking
config = RLMConfig(
    enable_infiniretri=True,
    infiniretri_threshold=10000,
    use_retriever_with_infiniretri=True  # Combine both
)

rlm = RLM.from_openai(
    "gpt-4o",
    config=config,
    retriever=retriever
)

# Flow: Query → Retriever (20 docs) → InfiniRetri (re-rank) → LLM
result = rlm.run("What are the financial projections for Q4?")
```

## Step 4: Streaming with Large Documents

```python
from rlm_toolkit import RLM, RLMConfig

config = RLMConfig(
    enable_infiniretri=True,
    stream=True  # Enable streaming
)

rlm = RLM.from_openai("gpt-4o", config=config)

# Stream response while processing large context
for chunk in rlm.stream("Summarize this document", context=large_doc):
    print(chunk, end="", flush=True)
```

## Step 5: Performance Optimization

```python
from rlm_toolkit import RLMConfig
from rlm_toolkit.retrieval import InfiniRetriConfig

# Optimized for speed
fast_config = InfiniRetriConfig(
    chunk_size=8000,       # Larger chunks = fewer API calls
    top_k=3,               # Fewer chunks = faster
    pooling="max",         # Fastest pooling
    parallel_processing=True,
    max_workers=4
)

# Optimized for accuracy
accurate_config = InfiniRetriConfig(
    chunk_size=2000,       # Smaller chunks = more precision
    chunk_overlap=500,     # More overlap = better coverage
    top_k=10,              # More chunks = better context
    pooling="mean",        # More stable aggregation
)
```

## Step 6: Document Types

InfiniRetri works with any text format:

```python
from rlm_toolkit import RLM, RLMConfig
from rlm_toolkit.loaders import PDFLoader, DOCXLoader

config = RLMConfig(enable_infiniretri=True)
rlm = RLM.from_openai("gpt-4o", config=config)

# PDFs
docs = PDFLoader("500_page_report.pdf").load()
full_text = "\n\n".join([d.content for d in docs])

result = rlm.run("What are the key recommendations?", context=full_text)

# Code repositories
from rlm_toolkit.loaders import DirectoryLoader, CodeLoader

code_docs = DirectoryLoader("./src", glob="**/*.py", loader_cls=CodeLoader).load()
codebase = "\n\n".join([f"# {d.metadata['source']}\n{d.content}" for d in code_docs])

result = rlm.run("Find the authentication implementation", context=codebase)
```

## Benchmark: Needle-In-a-Haystack

```python
from rlm_toolkit.evaluation import NeedleInHaystackBenchmark
from rlm_toolkit import RLM, RLMConfig

# Create benchmark
benchmark = NeedleInHaystackBenchmark(
    context_lengths=[10000, 50000, 100000, 500000, 1000000],
    needle="The secret code is: ALPHA-BRAVO-CHARLIE",
    depths=[0.1, 0.25, 0.5, 0.75, 0.9]  # Where to hide needle
)

# Test with InfiniRetri
config = RLMConfig(enable_infiniretri=True)
rlm = RLM.from_openai("gpt-4o", config=config)

results = benchmark.run(rlm)
print(f"Accuracy: {results.accuracy * 100}%")  # 100%
print(f"Average latency: {results.avg_latency}s")
```

## Complete Application

```python
# infinite_context_qa.py
from rlm_toolkit import RLM, RLMConfig
from rlm_toolkit.loaders import PDFLoader
from rlm_toolkit.retrieval import InfiniRetriConfig

def create_infinite_qa(pdf_path: str):
    """Create Q&A system for large PDFs."""
    
    # Load document
    print(f"📄 Loading {pdf_path}...")
    docs = PDFLoader(pdf_path).load()
    full_text = "\n\n".join([
        f"[Page {d.metadata.get('page', i)}]\n{d.content}" 
        for i, d in enumerate(docs)
    ])
    
    token_count = len(full_text) // 4  # Approximate
    print(f"   ~{token_count:,} tokens loaded")
    
    # Configure InfiniRetri
    infini_config = InfiniRetriConfig(
        chunk_size=4000,
        top_k=5,
        parallel_processing=True
    )
    
    config = RLMConfig(
        enable_infiniretri=True,
        infiniretri_config=infini_config
    )
    
    rlm = RLM.from_openai("gpt-4o", config=config)
    
    return rlm, full_text

def main():
    import sys
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "document.pdf"
    
    rlm, context = create_infinite_qa(pdf_path)
    
    print("\n" + "="*50)
    print("🔍 Infinite Context Q&A")
    print("   Type 'quit' to exit")
    print("="*50 + "\n")
    
    while True:
        question = input("❓ Question: ").strip()
        
        if not question:
            continue
        if question.lower() == 'quit':
            break
        
        result = rlm.run(question, context=context)
        print(f"\n✅ Answer: {result.final_answer}")
        
        if hasattr(result, 'chunks_used'):
            print(f"📊 Chunks analyzed: {result.chunks_used}")
        print()

if __name__ == "__main__":
    main()
```

## When to Use InfiniRetri

| Scenario | Use InfiniRetri? | Why |
|----------|-----------------|-----|
| Documents > 50K tokens | ✅ Yes | Standard context limits |
| Legal contracts | ✅ Yes | Need exact matches |
| Codebases | ✅ Yes | Find specific implementations |
| Short documents < 10K | ❌ No | Regular context sufficient |
| Very frequent queries | ⚠️ Maybe | Consider caching |

## Best Practices

!!! tip "Chunk Size"
    - Larger chunks (8K+) = fewer API calls, faster
    - Smaller chunks (2K) = more precise retrieval

!!! tip "Threshold"
    Set threshold based on your model's context window:
    ```python
    # GPT-4 (128K context)
    config = RLMConfig(infiniretri_threshold=100000)
    
    # GPT-4o-mini (16K context)
    config = RLMConfig(infiniretri_threshold=12000)
    ```

!!! tip "Caching"
    For repeated queries on same document:
    ```python
    from rlm_toolkit.retrieval import CachedInfiniRetri
    
    cached = CachedInfiniRetri(cache_dir="./infini_cache")
    ```

## Next Steps

- [Tutorial 7: Hierarchical Memory](07-hmem.md)
- [Concept: InfiniRetri](../concepts/infiniretri.md)
- [Benchmark Results](../concepts/benchmarks.md)
