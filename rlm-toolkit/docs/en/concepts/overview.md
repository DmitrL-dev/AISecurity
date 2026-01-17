# Overview

RLM-Toolkit is a comprehensive framework for building AI applications with Large Language Models.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    RLM Engine                        │
├─────────────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────┐  │
│  │Provider │ │ Memory  │ │Retriever│ │  Tools    │  │
│  │(LLM)    │ │(H-MEM)  │ │(Infini) │ │           │  │
│  └─────────┘ └─────────┘ └─────────┘ └───────────┘  │
├─────────────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────┐  │
│  │Loaders  │ │Splitters│ │  Embed  │ │VectorStore│  │
│  └─────────┘ └─────────┘ └─────────┘ └───────────┘  │
└─────────────────────────────────────────────────────┘
```

## Core Components

### RLM Engine
The central orchestrator that manages the REPL loop:

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")
result = rlm.run("Your query")
```

### Providers
Interfaces to 75+ LLM providers:

- **OpenAI**: GPT-4o, GPT-4, GPT-3.5
- **Anthropic**: Claude 3.5, Claude 3
- **Google**: Gemini Pro, Gemini Ultra
- **Local**: Ollama, vLLM, llama.cpp
- **And 70+ more...**

### Memory Systems

| Type | Description |
|------|-------------|
| **Buffer** | Simple conversation buffer |
| **Episodic** | Entity-based memory |
| **H-MEM** | 4-level hierarchical memory ⭐ |

### Document Loaders
135+ loaders for various sources:

- **Files**: PDF, DOCX, CSV, JSON, Markdown
- **Web**: URLs, Sitemaps, YouTube
- **Cloud**: S3, GCS, Azure Blob
- **APIs**: Slack, Notion, GitHub, Jira

### Vector Stores
20+ vector databases:

- **Managed**: Pinecone, Weaviate, Qdrant
- **Self-hosted**: Chroma, Milvus, pgvector
- **Serverless**: Supabase, Neon

### Embeddings
15+ embedding providers:

- **Cloud**: OpenAI, Cohere, Voyage
- **Local**: BGE, E5, GTE

## Unique Features

### InfiniRetri
Attention-based retrieval for infinite context:

```python
config = RLMConfig(enable_infiniretri=True)
rlm = RLM.from_openai("gpt-4o", config=config)
```

### H-MEM (Hierarchical Memory)
4-level memory with LLM consolidation:

```python
from rlm_toolkit.memory import HierarchicalMemory
memory = HierarchicalMemory()
```

### Self-Evolving
LLMs that improve with usage:

```python
from rlm_toolkit.evolve import SelfEvolvingRLM
evolving = SelfEvolvingRLM(provider, strategy="challenger_solver")
```

### Multi-Agent
Decentralized P2P agents:

```python
from rlm_toolkit.agents import MultiAgentRuntime, SecureAgent
runtime = MultiAgentRuntime()
```

## Security

RLM-Toolkit includes SENTINEL security features:

- **Secure REPL**: CIRCLE-compliant sandbox
- **Trust Zones**: Memory isolation
- **Audit Logging**: Full operation history

## Next Steps

- [Quickstart](../quickstart.md)
- [First Tutorial](../tutorials/01-first-app.md)
