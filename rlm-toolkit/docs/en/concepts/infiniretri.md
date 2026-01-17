# InfiniRetri Concept

InfiniRetri is RLM-Toolkit's breakthrough attention-based retrieval system for infinite context.

## The Problem

Standard LLMs have context limits:
- GPT-4: 128K tokens
- Claude 3: 200K tokens
- But real documents can be **millions of tokens**

Traditional solutions (RAG, chunking) lose information and accuracy.

## The Solution: InfiniRetri

InfiniRetri uses **attention-based retrieval** instead of embeddings:

```
┌─────────────────────────────────────────────────────────────────┐
│                Traditional RAG vs InfiniRetri                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Traditional RAG:                                                │
│  Document → Embed → VectorDB → Top-K → LLM                      │
│  • Loses semantic nuance during embedding                       │
│  • Top-K may miss relevant chunks                               │
│  • ~85% accuracy on needle-in-haystack                         │
│                                                                  │
│  InfiniRetri:                                                   │
│  Document → Chunk → Process each → Attention weights → Select   │
│  • Uses LLM's own attention mechanism                          │
│  • Query-aware selection                                        │
│  • 100% accuracy on needle-in-haystack                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## How It Works

1. **Chunking**: Document split into segments
2. **Attention Probing**: Each segment processed with query
3. **Weight Extraction**: Extract attention weights for query tokens
4. **Selection**: Top-K segments by attention score
5. **Synthesis**: LLM generates answer from selected context

## Key Benefits

| Feature | Benefit |
|---------|---------|
| **100% Accuracy** | Never misses the needle |
| **O(1) Memory** | Constant memory regardless of doc size |
| **No Embeddings** | No embedding model needed |
| **Query-Adaptive** | Selection tuned to specific query |

## Configuration

```python
from rlm_toolkit import RLMConfig
from rlm_toolkit.retrieval import InfiniRetriConfig

infini_config = InfiniRetriConfig(
    chunk_size=4000,        # Tokens per chunk
    chunk_overlap=200,      # Overlap for continuity
    top_k=5,                # Chunks to retrieve
    attention_layer=-1,     # Last layer attention
    pooling="mean"          # Attention aggregation
)

config = RLMConfig(
    enable_infiniretri=True,
    infiniretri_config=infini_config,
    infiniretri_threshold=50000
)
```

## When to Use

| Scenario | Use InfiniRetri? |
|----------|------------------|
| Documents > 50K tokens | ✅ Yes |
| Legal/Contract analysis | ✅ Yes |
| Codebase search | ✅ Yes |
| Short docs < 10K | ❌ No |

## Related

- [Tutorial: InfiniRetri](../tutorials/06-infiniretri.md)
- [Concept: RAG Pipeline](./rag.md)
