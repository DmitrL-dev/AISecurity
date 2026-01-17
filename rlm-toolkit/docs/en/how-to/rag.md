# How-to: Build RAG Pipelines

Recipes for building Retrieval-Augmented Generation systems.

## Basic RAG Pipeline

```python
from rlm_toolkit import RLM
from rlm_toolkit.loaders import PDFLoader
from rlm_toolkit.splitters import RecursiveTextSplitter
from rlm_toolkit.embeddings import OpenAIEmbeddings
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.retrievers import VectorStoreRetriever

docs = PDFLoader("document.pdf").load()
chunks = RecursiveTextSplitter(chunk_size=1000).split_documents(docs)

embeddings = OpenAIEmbeddings("text-embedding-3-small")
vs = ChromaVectorStore.from_documents(chunks, embeddings)

retriever = VectorStoreRetriever(vs, search_kwargs={"k": 5})
rlm = RLM.from_openai("gpt-4o")
rlm.set_retriever(retriever)

response = rlm.run("What is this document about?")
```

## Hybrid Search

```python
from rlm_toolkit.retrievers import HybridRetriever

retriever = HybridRetriever(
    vectorstore=vs,
    keyword_weight=0.3,
    semantic_weight=0.7
)
```

## Multi-Query Retriever

```python
from rlm_toolkit.retrievers import MultiQueryRetriever

retriever = MultiQueryRetriever(
    vectorstore=vs,
    llm=RLM.from_openai("gpt-4o-mini"),
    num_queries=3
)
```

## Re-ranking

```python
from rlm_toolkit.retrievers import ReRankRetriever

retriever = ReRankRetriever(
    base_retriever=vs.as_retriever(k=20),
    reranker="cross-encoder/ms-marco-MiniLM-L-12-v2",
    top_k=5
)
```

## InfiniRetri (Large Docs)

```python
from rlm_toolkit import RLMConfig
from rlm_toolkit.retrieval import InfiniRetriConfig

config = RLMConfig(
    enable_infiniretri=True,
    infiniretri_config=InfiniRetriConfig(
        chunk_size=4000,
        top_k=5
    ),
    infiniretri_threshold=50000
)

rlm = RLM.from_openai("gpt-4o", config=config)
```

## Add Source Citations

```python
rlm = RLM.from_openai("gpt-4o")
rlm.set_retriever(retriever)
rlm.set_system_prompt("""
Answer based on the provided context.
Always cite your sources with [Source: filename].
If unsure, say "I don't know."
""")
```

## Evaluate RAG

```python
from rlm_toolkit.evaluation import RAGEvaluator

evaluator = RAGEvaluator(retriever=retriever, generator=rlm)
results = evaluator.evaluate(
    questions=["What is X?"],
    ground_truth=["X is..."],
    metrics=["answer_relevancy", "faithfulness"]
)
```

## Related

- [Concept: RAG](../concepts/rag.md)
- [Tutorial: RAG](../tutorials/03-rag.md)
- [Tutorial: InfiniRetri](../tutorials/06-infiniretri.md)
