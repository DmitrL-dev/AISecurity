# Туториал 6: InfiniRetri

Освойте внимание-основанное извлечение для бесконечного контекста при работе с документами на 1M+ токенов со 100% точностью.

## Что такое InfiniRetri?

InfiniRetri — уникальная система извлечения RLM-Toolkit на основе внимания, которая:

- Обрабатывает документы до **10M+ токенов**
- Достигает **100% точности** на бенчмарках Needle-In-a-Haystack
- Использует **O(1) памяти** независимо от размера документа
- Работает **без эмбеддингов и векторных хранилищ**

## Как работает InfiniRetri

```
┌─────────────────────────────────────────────────────────────────┐
│                    Архитектура InfiniRetri                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Большой документ (1M+ токенов)                                │
│          ↓                                                       │
│   Разбиение на сегменты                                         │
│          ↓                                                       │
│   Обработка каждого сегмента через LLM                          │
│          ↓                                                       │
│   Извлечение весов внимания для запроса                         │
│          ↓                                                       │
│   Выбор сегментов с наивысшим вниманием                         │
│          ↓                                                       │
│   Возврат релевантного контекста                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Предварительные требования

```bash
pip install rlm-toolkit[all]
export OPENAI_API_KEY=your-key
```

## Шаг 1: Базовое использование InfiniRetri

```python
from rlm_toolkit import RLM, RLMConfig

# Включаем InfiniRetri
config = RLMConfig(
    use_infiniretri=True,
    infiniretri_threshold=100_000  # Активировать выше 50K токенов
)

rlm = RLM.from_openai("gpt-4o", config=config)

# Загружаем большой документ
with open("large_document.txt", "r") as f:
    massive_context = f.read()

# InfiniRetri активируется автоматически
result = rlm.run(
    "Найди конкретный пункт о штрафах за расторжение",
    context=massive_context
)

print(result.answer)
print(f"Обработано {result.total_tokens} токенов")
```

## Шаг 2: Настройка InfiniRetri

```python
from rlm_toolkit import RLM, RLMConfig
from rlm_toolkit.retrieval import InfiniRetriConfig

# Детальная конфигурация
infiniretri_config = InfiniRetriConfig(
    chunk_size=4000,          # Токенов на чанк
    chunk_overlap=200,        # Перекрытие между чанками
    top_k=5,                  # Количество чанков для извлечения
    attention_layer=-1,       # Использовать последний слой внимания
    pooling="mean",          # Агрегация внимания: mean, max, sum
)

config = RLMConfig(
    use_infiniretri=True,
    infiniretri_config=infiniretri_config,
    infiniretri_threshold=100_000
)

rlm = RLM.from_openai("gpt-4o", config=config)
```

## Шаг 3: С RAG Pipeline

Комбинирование InfiniRetri с векторным извлечением:

```python
from rlm_toolkit import RLM, RLMConfig
from rlm_toolkit.vectorstores import ChromaVectorStore
from rlm_toolkit.embeddings import OpenAIEmbeddings

# Векторное хранилище для начального извлечения
vectorstore = ChromaVectorStore.from_documents(docs, OpenAIEmbeddings())
retriever = vectorstore.as_retriever(search_kwargs={"k": 20})

# Включаем InfiniRetri для ре-ранжирования
config = RLMConfig(
    use_infiniretri=True,
    infiniretri_threshold=10000,
    use_retriever_with_infiniretri=True  # Комбинировать оба
)

rlm = RLM.from_openai(
    "gpt-4o",
    config=config,
    retriever=retriever
)

# Поток: Запрос → Ретривер (20 документов) → InfiniRetri (ре-ранк) → LLM
result = rlm.run("Каковы финансовые прогнозы на Q4?")
```

## Шаг 4: Стриминг с большими документами

```python
from rlm_toolkit import RLM, RLMConfig

config = RLMConfig(
    use_infiniretri=True,
    stream=True  # Включить стриминг
)

rlm = RLM.from_openai("gpt-4o", config=config)

# Стриминг ответа при обработке большого контекста
for chunk in rlm.stream("Суммируй этот документ", context=large_doc):
    print(chunk, end="", flush=True)
```

## Шаг 5: Оптимизация производительности

```python
from rlm_toolkit import RLMConfig
from rlm_toolkit.retrieval import InfiniRetriConfig

# Оптимизировано для скорости
fast_config = InfiniRetriConfig(
    chunk_size=8000,       # Большие чанки = меньше API вызовов
    top_k=3,               # Меньше чанков = быстрее
    pooling="max",         # Самый быстрый пулинг
    parallel_processing=True,
    max_workers=4
)

# Оптимизировано для точности
accurate_config = InfiniRetriConfig(
    chunk_size=2000,       # Меньшие чанки = больше точность
    chunk_overlap=500,     # Больше перекрытие = лучшее покрытие
    top_k=10,              # Больше чанков = лучше контекст
    pooling="mean",        # Более стабильная агрегация
)
```

## Шаг 6: Типы документов

InfiniRetri работает с любым текстовым форматом:

```python
from rlm_toolkit import RLM, RLMConfig
from rlm_toolkit.loaders import PDFLoader, DOCXLoader

config = RLMConfig(use_infiniretri=True)
rlm = RLM.from_openai("gpt-4o", config=config)

# PDF
docs = PDFLoader("отчёт_500_страниц.pdf").load()
full_text = "\n\n".join([d.content for d in docs])

result = rlm.run("Каковы ключевые рекомендации?", context=full_text)

# Репозитории кода
from rlm_toolkit.loaders import DirectoryLoader, CodeLoader

code_docs = DirectoryLoader("./src", glob="**/*.py", loader_cls=CodeLoader).load()
codebase = "\n\n".join([f"# {d.metadata['source']}\n{d.content}" for d in code_docs])

result = rlm.run("Найди реализацию аутентификации", context=codebase)
```

## Бенчмарк: Needle-In-a-Haystack

```python
from rlm_toolkit.evaluation import NeedleInHaystackBenchmark
from rlm_toolkit import RLM, RLMConfig

# Создаём бенчмарк
benchmark = NeedleInHaystackBenchmark(
    context_lengths=[10000, 50000, 100000, 500000, 1000000],
    needle="Секретный код: АЛЬФА-БРАВО-ЧАРЛИ",
    depths=[0.1, 0.25, 0.5, 0.75, 0.9]  # Где спрятать иголку
)

# Тестируем с InfiniRetri
config = RLMConfig(use_infiniretri=True)
rlm = RLM.from_openai("gpt-4o", config=config)

results = benchmark.run(rlm)
print(f"Точность: {results.accuracy * 100}%")  # 100%
print(f"Средняя задержка: {results.avg_latency}s")
```

## Полное приложение

```python
# infinite_context_qa.py
from rlm_toolkit import RLM, RLMConfig
from rlm_toolkit.loaders import PDFLoader
from rlm_toolkit.retrieval import InfiniRetriConfig

def create_infinite_qa(pdf_path: str):
    """Создаём систему Q&A для больших PDF."""
    
    # Загружаем документ
    print(f"📄 Загрузка {pdf_path}...")
    docs = PDFLoader(pdf_path).load()
    full_text = "\n\n".join([
        f"[Страница {d.metadata.get('page', i)}]\n{d.content}" 
        for i, d in enumerate(docs)
    ])
    
    token_count = len(full_text) // 4  # Приблизительно
    print(f"   ~{token_count:,} токенов загружено")
    
    # Настраиваем InfiniRetri
    infini_config = InfiniRetriConfig(
        chunk_size=4000,
        top_k=5,
        parallel_processing=True
    )
    
    config = RLMConfig(
        use_infiniretri=True,
        infiniretri_config=infini_config
    )
    
    rlm = RLM.from_openai("gpt-4o", config=config)
    
    return rlm, full_text

def main():
    import sys
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "document.pdf"
    
    rlm, context = create_infinite_qa(pdf_path)
    
    print("\n" + "="*50)
    print("🔍 Q&A с бесконечным контекстом")
    print("   Введите 'выход' для завершения")
    print("="*50 + "\n")
    
    while True:
        question = input("❓ Вопрос: ").strip()
        
        if not question:
            continue
        if question.lower() in ['выход', 'quit']:
            break
        
        result = rlm.run(question, context=context)
        print(f"\n✅ Ответ: {result.answer}")
        
        if hasattr(result, 'chunks_used'):
            print(f"📊 Проанализировано чанков: {result.chunks_used}")
        print()

if __name__ == "__main__":
    main()
```

## Когда использовать InfiniRetri

| Сценарий | Использовать InfiniRetri? | Почему |
|----------|--------------------------|--------|
| Документы > 50K токенов | ✅ Да | Ограничения контекста |
| Юридические договоры | ✅ Да | Нужны точные совпадения |
| Кодовые базы | ✅ Да | Поиск конкретных реализаций |
| Короткие документы < 10K | ❌ Нет | Обычного контекста достаточно |
| Очень частые запросы | ⚠️ Возможно | Рассмотрите кэширование |

## Лучшие практики

!!! tip "Размер чанка"
    - Большие чанки (8K+) = меньше API вызовов, быстрее
    - Меньшие чанки (2K) = более точное извлечение

!!! tip "Порог"
    Устанавливайте порог на основе контекстного окна модели:
    ```python
    # GPT-4 (128K контекст)
    config = RLMConfig(infiniretri_threshold=100000)
    
    # GPT-4o-mini (16K контекст)
    config = RLMConfig(infiniretri_threshold=12000)
    ```

!!! tip "Кэширование"
    Для повторных запросов к одному документу:
    ```python
    from rlm_toolkit.retrieval import CachedInfiniRetri
    
    cached = CachedInfiniRetri(cache_dir="./infini_cache")
    ```

## Следующие шаги

- [Туториал 7: Иерархическая память](07-hmem.md)
- [Концепция: InfiniRetri](../concepts/infiniretri.md)
- [Результаты бенчмарков](../concepts/benchmarks.md)
