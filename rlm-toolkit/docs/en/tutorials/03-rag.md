# Tutorial 3: RAG Pipeline

Build a complete Retrieval-Augmented Generation (RAG) system for answering questions from documents.

## What You'll Build

A RAG system that:

1. Loads PDFs and other documents
2. Chunks and embeds content
3. Stores in a vector database
4. Retrieves relevant context for queries
5. Generates accurate answers

## Understanding RAG

```
┌─────────────────────────────────────────────────────────────────┐
│                        RAG Pipeline                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Document → Loader → Splitter → Embeddings → VectorStore        │
│                                                     ↓            │
│   Query → Embeddings → Retriever → Context + Query → LLM → Answer│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

```bash
pip install rlm-toolkit[all]
export OPENAI_API_KEY=your-key
```

## Step 1: Load Documents

RLM-Toolkit supports 135+ document loaders:

```python
from rlm_toolkit.loaders import (
    PDFLoader,
    TextLoader,
    DOCXLoader,
    MarkdownLoader,
    WebPageLoader
)

# Load a PDF
pdf_docs = PDFLoader("report.pdf").load()
print(f"Loaded {len(pdf_docs)} pages")

# Load a web page
web_docs = WebPageLoader("https://example.com/article").load()

# Load multiple files
from rlm_toolkit.loaders import DirectoryLoader

all_docs = DirectoryLoader(
    "./documents",
    glob="**/*.pdf",
    loader_cls=PDFLoader
).load()
```

## Step 2: Split Documents

Large documents need to be split into smaller chunks:

```python
from rlm_toolkit.splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,       # Characters per chunk
    chunk_overlap=200,     # Overlap between chunks
    separators=["\n\n", "\n", ". ", " ", ""]
)

chunks = splitter.split_documents(pdf_docs)
print(f"Created {len(chunks)} chunks")
```

### Choosing Chunk Parameters

| Document Type | chunk_size | chunk_overlap |
|--------------|------------|---------------|
| Technical docs | 1000-1500 | 200 |
| Legal documents | 500-800 | 100 |
| Conversations | 200-400 | 50 |
| Code | 1500-2000 | 300 |

## Step 3: Create Embeddings

```python
from rlm_toolkit.embeddings import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)

# Test embedding
test_embedding = embeddings.embed_query("Hello world")
print(f"Embedding dimension: {len(test_embedding)}")
```

### Available Embedding Providers

```python
# OpenAI
from rlm_toolkit.embeddings import OpenAIEmbeddings
embeddings = OpenAIEmbeddings()

# Cohere
from rlm_toolkit.embeddings import CohereEmbeddings
embeddings = CohereEmbeddings()

# Local BGE
from rlm_toolkit.embeddings import BGEEmbeddings
embeddings = BGEEmbeddings(model_name="BAAI/bge-small-en-v1.5")

# Voyage AI
from rlm_toolkit.embeddings import VoyageEmbeddings
embeddings = VoyageEmbeddings()
```

## Step 4: Store in Vector Database

```python
from rlm_toolkit.vectorstores import ChromaVectorStore

# Create and populate
vectorstore = ChromaVectorStore.from_documents(
    chunks,
    embeddings,
    collection_name="my-documents",
    persist_directory="./chroma_db"
)

print(f"Stored {vectorstore.count()} vectors")
```

### Other Vector Stores

```python
# Pinecone (managed)
from rlm_toolkit.vectorstores import PineconeVectorStore
vectorstore = PineconeVectorStore.from_documents(
    chunks, embeddings,
    index_name="my-index"
)

# Qdrant (self-hosted)
from rlm_toolkit.vectorstores import QdrantVectorStore
vectorstore = QdrantVectorStore.from_documents(
    chunks, embeddings,
    url="http://localhost:6333",
    collection_name="my-docs"
)

# PostgreSQL (pgvector)
from rlm_toolkit.vectorstores import PgVectorStore
vectorstore = PgVectorStore.from_documents(
    chunks, embeddings,
    connection_string="postgresql://user:pass@localhost/db"
)
```

## Step 5: Create Retriever

```python
# Basic retriever
retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 5}  # Top 5 results
)

# With score threshold
retriever = vectorstore.as_retriever(
    search_type="similarity_score_threshold",
    search_kwargs={"score_threshold": 0.7, "k": 10}
)

# MMR (Maximum Marginal Relevance) for diversity
retriever = vectorstore.as_retriever(
    search_type="mmr",
    search_kwargs={"k": 5, "fetch_k": 20, "lambda_mult": 0.5}
)
```

## Step 6: Query with RLM

```python
from rlm_toolkit import RLM

# Create RLM with retriever
rlm = RLM.from_openai(
    "gpt-4o",
    retriever=retriever
)

# Ask questions
result = rlm.run("What are the key findings in the report?")
print(result.final_answer)

# Access retrieved documents
for doc in result.context_documents:
    print(f"Source: {doc.metadata.get('source')}")
    print(f"Content: {doc.content[:200]}...")
```

## Complete RAG Application

```python
# rag_app.py
from rlm_toolkit import RLM
from rlm_toolkit.loaders import PDFLoader, DirectoryLoader
from rlm_toolkit.splitters import RecursiveCharacterTextSplitter
from rlm_toolkit.embeddings import OpenAIEmbeddings
from rlm_toolkit.vectorstores import ChromaVectorStore
import os

class RAGApplication:
    def __init__(self, docs_directory: str, persist_dir: str = "./rag_db"):
        self.docs_directory = docs_directory
        self.persist_dir = persist_dir
        self.vectorstore = None
        self.rlm = None
    
    def index_documents(self):
        """Load and index all documents."""
        print("📄 Loading documents...")
        
        # Load all PDFs
        loader = DirectoryLoader(
            self.docs_directory,
            glob="**/*.pdf",
            loader_cls=PDFLoader,
            show_progress=True
        )
        documents = loader.load()
        print(f"   Loaded {len(documents)} documents")
        
        # Split into chunks
        print("✂️ Splitting into chunks...")
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = splitter.split_documents(documents)
        print(f"   Created {len(chunks)} chunks")
        
        # Create embeddings and store
        print("🧮 Creating embeddings...")
        embeddings = OpenAIEmbeddings()
        
        self.vectorstore = ChromaVectorStore.from_documents(
            chunks,
            embeddings,
            collection_name="rag-docs",
            persist_directory=self.persist_dir
        )
        print(f"   Stored {self.vectorstore.count()} vectors")
        
        return self
    
    def load_existing(self):
        """Load existing vector store."""
        embeddings = OpenAIEmbeddings()
        self.vectorstore = ChromaVectorStore(
            collection_name="rag-docs",
            embedding_function=embeddings,
            persist_directory=self.persist_dir
        )
        print(f"📦 Loaded {self.vectorstore.count()} vectors")
        return self
    
    def setup_rlm(self):
        """Create RLM with retriever."""
        retriever = self.vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 5}
        )
        
        self.rlm = RLM.from_openai(
            "gpt-4o",
            retriever=retriever,
            system_prompt="""You are a helpful assistant that answers questions 
            based on the provided documents. Always cite your sources.
            If you don't find relevant information, say so."""
        )
        return self
    
    def query(self, question: str) -> str:
        """Query the RAG system."""
        result = self.rlm.run(question)
        return result.final_answer
    
    def interactive(self):
        """Run interactive Q&A session."""
        print("\n" + "="*50)
        print("📚 RAG System Ready!")
        print("   Type 'quit' to exit")
        print("="*50 + "\n")
        
        while True:
            question = input("❓ Question: ")
            if question.lower() == 'quit':
                break
            
            answer = self.query(question)
            print(f"\n✅ Answer: {answer}\n")

def main():
    # Check if index exists
    if os.path.exists("./rag_db"):
        app = RAGApplication("./documents").load_existing()
    else:
        app = RAGApplication("./documents").index_documents()
    
    app.setup_rlm().interactive()

if __name__ == "__main__":
    main()
```

## Advanced: Using InfiniRetri

For very large documents (100K+ tokens), use InfiniRetri:

```python
from rlm_toolkit import RLM, RLMConfig

config = RLMConfig(
    enable_infiniretri=True,
    infiniretri_threshold=50000  # Token threshold
)

rlm = RLM.from_openai(
    "gpt-4o",
    config=config,
    retriever=retriever
)

# InfiniRetri automatically activates for large contexts
result = rlm.run("Find the specific clause about liability")
```

## Best Practices

!!! tip "Chunk Size"
    Choose chunk size based on your content:
    - Too small: loses context
    - Too large: retrieves irrelevant info

!!! tip "Embedding Model"
    Match embedding model to your use case:
    - `text-embedding-3-small`: Fast, good for most cases
    - `text-embedding-3-large`: Higher quality, more expensive

!!! tip "Retrieval Strategy"
    - Use MMR for diverse results
    - Use score threshold to filter low-quality matches

!!! warning "Cost Management"
    Embedding large document sets can be expensive. 
    Use `batch_size` parameter to control API calls.

## Next Steps

- [Tutorial 4: Agents](04-agents.md)
- [Concept: InfiniRetri](../concepts/infiniretri.md)
- [How-to: Document Loaders](../how-to/loaders.md)
