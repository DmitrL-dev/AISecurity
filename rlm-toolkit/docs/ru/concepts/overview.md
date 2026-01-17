# Обзор

RLM-Toolkit — комплексный фреймворк для создания AI-приложений с большими языковыми моделями.

## Архитектура

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

## Основные компоненты

### RLM Engine
Центральный оркестратор, управляющий REPL-циклом:

```python
from rlm_toolkit import RLM

rlm = RLM.from_openai("gpt-4o")
result = rlm.run("Ваш запрос")
```

### Провайдеры
Интерфейсы к 75+ LLM-провайдерам:

- **OpenAI**: GPT-4o, GPT-4, GPT-3.5
- **Anthropic**: Claude 3.5, Claude 3
- **Google**: Gemini Pro, Gemini Ultra
- **Локальные**: Ollama, vLLM, llama.cpp
- **И ещё 70+...**

### Системы памяти

| Тип | Описание |
|-----|----------|
| **Buffer** | Простой буфер разговора |
| **Episodic** | Память на основе сущностей |
| **H-MEM** | 4-уровневая иерархическая память ⭐ |

### Загрузчики документов
135+ загрузчиков для различных источников:

- **Файлы**: PDF, DOCX, CSV, JSON, Markdown
- **Веб**: URLs, Sitemaps, YouTube
- **Облако**: S3, GCS, Azure Blob
- **API**: Slack, Notion, GitHub, Jira

### Векторные хранилища
20+ векторных баз данных:

- **Управляемые**: Pinecone, Weaviate, Qdrant
- **Self-hosted**: Chroma, Milvus, pgvector
- **Serverless**: Supabase, Neon

### Эмбеддинги
15+ провайдеров эмбеддингов:

- **Облачные**: OpenAI, Cohere, Voyage
- **Локальные**: BGE, E5, GTE

## Уникальные возможности

### InfiniRetri
Внимание-основанное извлечение для бесконечного контекста:

```python
config = RLMConfig(enable_infiniretri=True)
rlm = RLM.from_openai("gpt-4o", config=config)
```

### H-MEM (Иерархическая память)
4-уровневая память с LLM-консолидацией:

```python
from rlm_toolkit.memory import HierarchicalMemory
memory = HierarchicalMemory()
```

### Self-Evolving
LLM, улучшающиеся с использованием:

```python
from rlm_toolkit.evolve import SelfEvolvingRLM
evolving = SelfEvolvingRLM(provider, strategy="challenger_solver")
```

### Multi-Agent
Децентрализованные P2P-агенты:

```python
from rlm_toolkit.agents import MultiAgentRuntime, SecureAgent
runtime = MultiAgentRuntime()
```

## Безопасность

RLM-Toolkit включает функции безопасности SENTINEL:

- **Secure REPL**: CIRCLE-совместимая песочница
- **Trust Zones**: Изоляция памяти
- **Audit Logging**: Полная история операций

## Следующие шаги

- [Быстрый старт](../quickstart.md)
- [Первый туториал](../tutorials/01-first-app.md)
