# How-to: Построение RAG пайплайнов

Рецепты построения систем Retrieval-Augmented Generation.

## Базовый RAG пайплайн

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

response = rlm.run("О чём этот документ?")
```

## Гибридный поиск

```python
from rlm_toolkit.retrievers import HybridRetriever

retriever = HybridRetriever(
    vectorstore=vs,
    keyword_weight=0.3,
    semantic_weight=0.7
)
```

## Multi-Query ретривер

```python
from rlm_toolkit.retrievers import MultiQueryRetriever

retriever = MultiQueryRetriever(
    vectorstore=vs,
    llm=RLM.from_openai("gpt-4o-mini"),
    num_queries=3
)
```

## Реранкинг

```python
from rlm_toolkit.retrievers import ReRankRetriever

retriever = ReRankRetriever(
    base_retriever=vs.as_retriever(k=20),
    reranker="cross-encoder/ms-marco-MiniLM-L-12-v2",
    top_k=5
)
```

## InfiniRetri (большие документы)

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

## Добавление цитат источников

```python
rlm = RLM.from_openai("gpt-4o")
rlm.set_retriever(retriever)
rlm.set_system_prompt("""
Отвечай на основе предоставленного контекста.
Всегда цитируй источники: [Источник: имя_файла].
Если не уверен, скажи "Не знаю."
""")
```

## Оценка RAG

```python
from rlm_toolkit.evaluation import RAGEvaluator

evaluator = RAGEvaluator(retriever=retriever, generator=rlm)
results = evaluator.evaluate(
    questions=["Что такое X?"],
    ground_truth=["X это..."],
    metrics=["answer_relevancy", "faithfulness"]
)
```

## Связанное

- [Концепция: RAG](../concepts/rag.md)
- [Туториал: RAG](../tutorials/03-rag.md)
- [Туториал: InfiniRetri](../tutorials/06-infiniretri.md)
