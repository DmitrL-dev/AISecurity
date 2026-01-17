# How-to: InfiniRetri (бесконечный контекст)

Рецепты работы с документами 1M+ токенов.

## Включение InfiniRetri

```python
from rlm_toolkit import RLM, RLMConfig
from rlm_toolkit.retrieval import InfiniRetriConfig

config = RLMConfig(
    enable_infiniretri=True,
    infiniretri_config=InfiniRetriConfig(
        chunk_size=4000,
        chunk_overlap=200,
        top_k=5,
        attention_layer=-1,
        pooling="mean"
    ),
    infiniretri_threshold=50000  # Использовать для документов > 50K токенов
)

rlm = RLM.from_openai("gpt-4o", config=config)
```

## Обработка длинных документов

```python
from rlm_toolkit.loaders import PDFLoader

# Загрузка документа 1000+ страниц
docs = PDFLoader("massive_document.pdf").load()

# InfiniRetri автоматически активируется
response = rlm.run_with_docs(
    query="Суммируй ключевые находки",
    documents=docs
)
```

## Настройка размера чанка

```python
config = InfiniRetriConfig(
    chunk_size=4000,      # Токенов на чанк (настраивать под модель)
    chunk_overlap=200,    # Перекрытие для непрерывности контекста
    top_k=5               # Топ чанков для извлечения
)
```

## Пользовательский слой внимания

```python
config = InfiniRetriConfig(
    attention_layer=-1,   # Последний слой (по умолчанию)
    # attention_layer=12  # Конкретный слой
    pooling="mean"        # mean, max, или first
)
```

## Пакетная обработка

```python
from rlm_toolkit import RLM
from rlm_toolkit.retrieval import InfiniRetri

infini = InfiniRetri(
    llm=RLM.from_openai("gpt-4o"),
    config=InfiniRetriConfig(chunk_size=4000, top_k=5)
)

# Обработка нескольких запросов
queries = ["Какая выручка?", "Кто ключевые стейкхолдеры?"]
results = []

for query in queries:
    result = infini.run(
        query=query,
        documents=docs
    )
    results.append(result)
```

## Оптимизация памяти

```python
config = InfiniRetriConfig(
    chunk_size=2000,          # Меньше чанки = меньше памяти
    top_k=3,                  # Меньше чанков = быстрее
    stream_chunks=True,       # Потоковая обработка
    offload_to_disk=True,     # Выгрузка на диск для огромных документов
    offload_path="./cache"
)
```

## Сравнение со стандартным RAG

```python
# Стандартный RAG (может пропустить информацию)
standard_result = rag.run("Найди иголку")  # ~85% точность

# InfiniRetri (на основе внимания)
infini_result = infini.run("Найди иголку")  # 100% точность
```

## Использование с векторным хранилищем

```python
from rlm_toolkit.retrieval import HybridInfiniRetri

# Комбинация векторный поиск + InfiniRetri
hybrid = HybridInfiniRetri(
    vectorstore=vectorstore,
    infini_config=InfiniRetriConfig(chunk_size=4000),
    vector_weight=0.3,
    attention_weight=0.7
)

result = hybrid.run(query, documents)
```

## Настройка производительности

| Размер документа | Размер чанка | Top-K | Память |
|------------------|--------------|-------|--------|
| < 100K токенов | 4000 | 5 | ~4GB |
| 100K - 500K | 4000 | 3 | ~8GB |
| 500K - 1M | 2000 | 3 | ~16GB |
| > 1M токенов | 2000 | 2 | ~32GB |

## Связанное

- [Концепция: InfiniRetri](../concepts/infiniretri.md)
- [Туториал: InfiniRetri](../tutorials/06-infiniretri.md)
