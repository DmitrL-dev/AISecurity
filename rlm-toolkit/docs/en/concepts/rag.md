# RAG (Retrieval-Augmented Generation)

RAG combines LLM generation with document retrieval for grounded, factual responses.

## What is RAG?

RAG enhances LLMs by:
1. **Retrieving** relevant documents from a knowledge base
2. **Augmenting** the prompt with retrieved context
3. **Generating** answers grounded in the retrieved information

```
┌─────────────────────────────────────────────────────────────────┐
│                    RAG Pipeline                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Query: "What is the company policy on remote work?"            │
│              ↓                                                   │
│         [RETRIEVE] → Search vector store                        │
│              ↓                                                   │
│        Relevant docs: [policy.pdf page 5, hr_manual.pdf]        │
│              ↓                                                   │
│         [AUGMENT] → Add to prompt                               │
│              ↓                                                   │
│         [GENERATE] → LLM answers with context                   │
│              ↓                                                   │
│        Answer: "According to the HR policy..."                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Basic RAG

```python
from rlm_toolkit import RLM
from rlm_toolkit.loaders import PDFLoader
from rlm_toolkit.splitters import RecursiveTextSplitter
from rlm_toolkit.embeddings import OpenAIEmbeddings
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.retrievers import VectorStoreRetriever

# 1. Load documents
docs = PDFLoader("company_policy.pdf").load()

# 2. Split into chunks
splitter = RecursiveTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = splitter.split_documents(docs)

# 3. Create embeddings and store
embeddings = OpenAIEmbeddings("text-embedding-3-small")
vectorstore = ChromaVectorStore.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="./db"
)

# 4. Create retriever
retriever = VectorStoreRetriever(
    vectorstore=vectorstore,
    search_type="similarity",
    search_kwargs={"k": 5}
)

# 5. Use with RLM
rlm = RLM.from_openai("gpt-4o")
rlm.set_retriever(retriever)

# 6. Query
response = rlm.run("What is the remote work policy?")
print(response)
```

## RAG Components

### Document Loaders

Load documents from various sources:

```python
from rlm_toolkit.loaders import (
    PDFLoader,
    DOCXLoader,
    WebPageLoader,
    DirectoryLoader
)

# Single file
docs = PDFLoader("report.pdf").load()

# Entire directory
docs = DirectoryLoader("./docs", glob="**/*.pdf").load()

# Web pages
docs = WebPageLoader("https://example.com/docs").load()
```

### Text Splitters

Split documents into chunks:

```python
from rlm_toolkit.splitters import (
    RecursiveTextSplitter,
    TokenTextSplitter,
    MarkdownSplitter,
    CodeSplitter
)

# General purpose
splitter = RecursiveTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", " ", ""]
)

# Token-based (recommended for models)
splitter = TokenTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    model="gpt-4o"
)

# Markdown-aware
splitter = MarkdownSplitter(
    chunk_size=1000,
    headers_to_split_on=["#", "##"]
)

# Code-aware
splitter = CodeSplitter(
    chunk_size=500,
    language="python"
)
```

### Embeddings

Convert text to vectors:

```python
from rlm_toolkit.embeddings import (
    OpenAIEmbeddings,
    CohereEmbeddings,
    HuggingFaceEmbeddings,
    OllamaEmbeddings
)

# OpenAI
embeddings = OpenAIEmbeddings("text-embedding-3-small")

# Cohere
embeddings = CohereEmbeddings("embed-english-v3.0")

# Local
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# Ollama
embeddings = OllamaEmbeddings(model="nomic-embed-text")
```

### Vector Stores

Store and search embeddings:

```python
from rlm_toolkit.vectorstores import (
    ChromaVectorStore,
    FAISSVectorStore,
    PineconeVectorStore,
    QdrantVectorStore
)

# Chroma (development)
vs = ChromaVectorStore.from_documents(docs, embeddings)

# FAISS (production)
vs = FAISSVectorStore.from_documents(docs, embeddings)

# Pinecone (cloud)
vs = PineconeVectorStore(index_name="my-index", embedding=embeddings)
```

### Retrievers

Search strategies:

```python
from rlm_toolkit.retrievers import (
    VectorStoreRetriever,
    MultiQueryRetriever,
    SelfQueryRetriever,
    ContextualCompressionRetriever
)

# Basic retriever
retriever = VectorStoreRetriever(vectorstore, search_kwargs={"k": 5})

# Multi-query (generates multiple queries for better recall)
retriever = MultiQueryRetriever(
    vectorstore=vectorstore,
    llm=RLM.from_openai("gpt-4o-mini"),
    num_queries=3
)

# Self-query (extracts filter from natural language)
retriever = SelfQueryRetriever(
    vectorstore=vectorstore,
    llm=RLM.from_openai("gpt-4o-mini"),
    metadata_fields=["category", "date", "author"]
)

# Compression (summarizes retrieved docs)
retriever = ContextualCompressionRetriever(
    vectorstore=vectorstore,
    compressor=RLM.from_openai("gpt-4o-mini")
)
```

## Advanced RAG Patterns

### Hybrid Search

Combine semantic + keyword:

```python
from rlm_toolkit.retrievers import HybridRetriever

retriever = HybridRetriever(
    vectorstore=vectorstore,
    keyword_weight=0.3,      # 30% keyword
    semantic_weight=0.7,     # 70% semantic
    fusion_method="rrf"       # Reciprocal Rank Fusion
)
```

### Re-ranking

```python
from rlm_toolkit.retrievers import ReRankRetriever

retriever = ReRankRetriever(
    base_retriever=vectorstore.as_retriever(k=20),
    reranker="cross-encoder/ms-marco-MiniLM-L-12-v2",
    top_k=5
)
```

### Parent Document Retriever

```python
from rlm_toolkit.retrievers import ParentDocumentRetriever

# Retrieves child chunks, returns parent documents
retriever = ParentDocumentRetriever(
    vectorstore=vectorstore,
    child_splitter=RecursiveTextSplitter(chunk_size=200),
    parent_splitter=RecursiveTextSplitter(chunk_size=2000)
)
```

### Ensemble Retriever

```python
from rlm_toolkit.retrievers import EnsembleRetriever

# Combine multiple retrievers
retriever = EnsembleRetriever(
    retrievers=[
        retriever_1,  # Vector search
        retriever_2,  # BM25
        retriever_3,  # Keyword
    ],
    weights=[0.5, 0.3, 0.2]
)
```

## RAG with InfiniRetri

For documents > 50K tokens:

```python
from rlm_toolkit import RLM, RLMConfig
from rlm_toolkit.retrieval import InfiniRetriConfig

config = RLMConfig(
    enable_infiniretri=True,
    infiniretri_config=InfiniRetriConfig(
        chunk_size=4000,
        chunk_overlap=200,
        top_k=5
    ),
    infiniretri_threshold=50000
)

rlm = RLM.from_openai("gpt-4o", config=config)

# Automatically uses InfiniRetri for long documents
response = rlm.run_with_docs(
    query="Summarize key points",
    documents=very_long_documents  # 1M+ tokens
)
```

## RAG Evaluation

```python
from rlm_toolkit.evaluation import RAGEvaluator

evaluator = RAGEvaluator(
    retriever=retriever,
    generator=rlm
)

results = evaluator.evaluate(
    questions=["What is X?", "How does Y work?"],
    ground_truth=["X is...", "Y works by..."],
    metrics=["answer_relevancy", "faithfulness", "context_recall"]
)

print(results)
# {
#   "answer_relevancy": 0.85,
#   "faithfulness": 0.92,
#   "context_recall": 0.78
# }
```

## Best Practices

!!! tip "Chunking Strategy"
    - Chunk size: 500-1000 tokens for most use cases
    - Include overlap (10-20%) for context continuity
    - Use semantic splitters for better boundaries

!!! tip "Retrieval Quality"
    - Start with k=5-10 documents
    - Use hybrid search for better recall
    - Re-rank for precision

!!! tip "Prompt Design"
    - Include source citations in prompt
    - Ask model to quote from context
    - Instruct to say "I don't know" when uncertain

!!! tip "Evaluation"
    - Test with ground truth answers
    - Monitor faithfulness (hallucinations)
    - Track context relevance

## Related

- [Tutorial: RAG Pipeline](../tutorials/03-rag.md)
- [Tutorial: InfiniRetri](../tutorials/06-infiniretri.md)
- [Concept: Loaders](./loaders.md)
- [Concept: Vector Stores](./vectorstores.md)
