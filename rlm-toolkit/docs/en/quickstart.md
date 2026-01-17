# Quickstart

Get RLM-Toolkit running in 5 minutes.

## Installation

=== "Basic"
    ```bash
    pip install rlm-toolkit
    ```

=== "With all providers"
    ```bash
    pip install rlm-toolkit[all]
    ```

=== "Development"
    ```bash
    git clone https://github.com/sentinel-community/rlm-toolkit
    cd rlm-toolkit
    pip install -e ".[dev]"
    ```

## Your First RLM

```python
from rlm_toolkit import RLM

# Create an RLM instance with OpenAI
rlm = RLM.from_openai("gpt-4o")

# Simple query
result = rlm.run("Explain quantum computing in simple terms")
print(result.final_answer)
```

!!! tip "API Key"
    Set your API key: `export OPENAI_API_KEY=your-key`

## With Memory

```python
from rlm_toolkit import RLM
from rlm_toolkit.memory import HierarchicalMemory

# Create memory-enabled RLM
memory = HierarchicalMemory()
rlm = RLM.from_openai("gpt-4o", memory=memory)

# First conversation
rlm.run("My name is Alex")

# Memory persists
result = rlm.run("What's my name?")
print(result.final_answer)  # "Your name is Alex"
```

## RAG Pipeline

```python
from rlm_toolkit import RLM
from rlm_toolkit.loaders import PDFLoader
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.embeddings import OpenAIEmbeddings

# Load documents
docs = PDFLoader("report.pdf").load()

# Create vector store
vectorstore = ChromaVectorStore.from_documents(
    docs, 
    OpenAIEmbeddings()
)

# Query with RAG
rlm = RLM.from_openai("gpt-4o", retriever=vectorstore.as_retriever())
result = rlm.run("What are the key findings?")
```

## Using InfiniRetri

For documents with 100K+ tokens:

```python
from rlm_toolkit import RLM, RLMConfig

config = RLMConfig(
    enable_infiniretri=True,
    infiniretri_threshold=50000
)

rlm = RLM.from_openai("gpt-4o", config=config)
result = rlm.run("Find the budget for Q3", context=massive_document)
```

## Next Steps

- [Tutorial: Build a Chatbot](tutorials/02-chatbot.md)
- [Tutorial: RAG Pipeline](tutorials/03-rag.md)
- [Concept: InfiniRetri](concepts/infiniretri.md)
- [Concept: H-MEM](concepts/hmem.md)
