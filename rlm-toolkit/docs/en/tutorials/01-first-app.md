# Tutorial 1: Your First Application

Build your first AI application with RLM-Toolkit in 15 minutes.

## What You'll Build

A simple question-answering system that:

1. Loads a document
2. Creates embeddings
3. Stores in a vector database
4. Answers questions about the document

## Prerequisites

```bash
pip install rlm-toolkit[all]
```

Set your OpenAI API key:
```bash
export OPENAI_API_KEY=your-api-key-here
```

## Step 1: Create the Project

Create a new directory and file:

```bash
mkdir my-first-rlm
cd my-first-rlm
touch app.py
```

## Step 2: Import Dependencies

```python
# app.py
from rlm_toolkit import RLM, RLMConfig
from rlm_toolkit.loaders import TextLoader
from rlm_toolkit.splitters import RecursiveCharacterTextSplitter
from rlm_toolkit.embeddings import OpenAIEmbeddings
from rlm_toolkit.vectorstores import ChromaVectorStore
```

## Step 3: Create Sample Data

Create a file `data.txt` with some content:

```text
RLM-Toolkit is a modern AI framework.
It supports 75+ LLM providers including OpenAI, Anthropic, and Google.
The framework includes 135+ document loaders for various file formats.
Unique features include InfiniRetri for infinite context and H-MEM for hierarchical memory.
RLM-Toolkit was designed as a secure alternative to LangChain.
```

## Step 4: Load and Process the Document

```python
# Load the document
loader = TextLoader("data.txt")
documents = loader.load()

print(f"Loaded {len(documents)} document(s)")
print(f"Content length: {len(documents[0].content)} characters")
```

## Step 5: Split into Chunks

```python
# Split into smaller chunks for better retrieval
splitter = RecursiveCharacterTextSplitter(
    chunk_size=100,
    chunk_overlap=20
)

chunks = splitter.split_documents(documents)
print(f"Split into {len(chunks)} chunks")
```

## Step 6: Create Embeddings and Store

```python
# Create embeddings
embeddings = OpenAIEmbeddings()

# Store in ChromaDB
vectorstore = ChromaVectorStore.from_documents(
    chunks,
    embeddings,
    collection_name="my-first-collection"
)

print("Vector store created!")
```

## Step 7: Create RLM with Retriever

```python
# Create retriever from vector store
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# Create RLM with retriever
rlm = RLM.from_openai(
    "gpt-4o-mini",
    retriever=retriever
)
```

## Step 8: Ask Questions

```python
# Ask questions about your document
questions = [
    "What is RLM-Toolkit?",
    "How many LLM providers are supported?",
    "What are the unique features?",
]

for question in questions:
    print(f"\n❓ {question}")
    result = rlm.run(question)
    print(f"✅ {result.final_answer}")
```

## Complete Code

```python
# app.py
from rlm_toolkit import RLM
from rlm_toolkit.loaders import TextLoader
from rlm_toolkit.splitters import RecursiveCharacterTextSplitter
from rlm_toolkit.embeddings import OpenAIEmbeddings
from rlm_toolkit.vectorstores import ChromaVectorStore

def main():
    # 1. Load document
    print("📄 Loading document...")
    loader = TextLoader("data.txt")
    documents = loader.load()
    
    # 2. Split into chunks
    print("✂️ Splitting into chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=100,
        chunk_overlap=20
    )
    chunks = splitter.split_documents(documents)
    print(f"   Created {len(chunks)} chunks")
    
    # 3. Create embeddings and store
    print("🧮 Creating embeddings...")
    embeddings = OpenAIEmbeddings()
    vectorstore = ChromaVectorStore.from_documents(
        chunks,
        embeddings,
        collection_name="my-first-collection"
    )
    
    # 4. Create RLM with retriever
    print("🤖 Initializing RLM...")
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    rlm = RLM.from_openai("gpt-4o-mini", retriever=retriever)
    
    # 5. Interactive Q&A
    print("\n" + "="*50)
    print("🎉 Ready! Ask questions about your document.")
    print("   Type 'quit' to exit.")
    print("="*50 + "\n")
    
    while True:
        question = input("You: ")
        if question.lower() in ['quit', 'exit', 'q']:
            break
        
        result = rlm.run(question)
        print(f"AI: {result.final_answer}\n")

if __name__ == "__main__":
    main()
```

## Run Your Application

```bash
python app.py
```

Expected output:
```
📄 Loading document...
✂️ Splitting into chunks...
   Created 5 chunks
🧮 Creating embeddings...
🤖 Initializing RLM...

==================================================
🎉 Ready! Ask questions about your document.
   Type 'quit' to exit.
==================================================

You: What is RLM-Toolkit?
AI: RLM-Toolkit is a modern AI framework designed as a secure 
    alternative to LangChain. It supports 75+ LLM providers 
    and includes unique features like InfiniRetri and H-MEM.
```

## What's Next?

- [Tutorial 2: Build a Chatbot](02-chatbot.md) — Add conversation memory
- [Tutorial 3: RAG Pipeline](03-rag.md) — Work with PDFs and large documents
- [Concept: Providers](../concepts/providers.md) — Learn about LLM providers

## Troubleshooting

!!! warning "API Key Error"
    If you see `AuthenticationError`, make sure your `OPENAI_API_KEY` is set correctly.

!!! warning "Import Error"
    If imports fail, reinstall with `pip install rlm-toolkit[all]`

!!! tip "Using Other Providers"
    Replace `RLM.from_openai()` with:
    
    - `RLM.from_anthropic("claude-3-sonnet")` for Claude
    - `RLM.from_ollama("llama3")` for local Ollama
