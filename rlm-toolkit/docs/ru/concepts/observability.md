# Observability

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **Трейсинг, метрики и контроль затрат** для production AI-приложений

## Обзор

RLM-Toolkit предоставляет комплексную наблюдаемость:
- **Tracer** — Распределённый трейсинг со спанами
- **CostTracker** — Мониторинг затрат LLM с бюджетами
- **Exporters** — Интеграция с Langfuse, LangSmith, OpenTelemetry

## Быстрый старт

```python
from rlm_toolkit import RLM
from rlm_toolkit.observability import Tracer, CostTracker

# Создаём tracer и cost tracker
tracer = Tracer(service_name="my-app")
cost_tracker = CostTracker(budget_usd=10.0)

# Внедряем в RLM
rlm = RLM.from_openai("gpt-4o", tracer=tracer, cost_tracker=cost_tracker)

# Все операции теперь трассируются
result = rlm.run("Суммаризируй этот документ", context=document)

# Получаем отчёт о затратах
report = cost_tracker.get_report()
print(f"Общая стоимость: ${report.total_cost:.4f}")
print(f"Остаток бюджета: ${report.remaining:.2f}")
```

## Трейсинг

### Базовый трейсинг

```python
from rlm_toolkit.observability import Tracer, Span

tracer = Tracer(service_name="my-service")

# Ручные спаны
with tracer.span("process_document") as span:
    span.set_attribute("document_size", len(doc))
    result = process(doc)
    span.set_attribute("result_size", len(result))
```

### Вложенные спаны

```python
with tracer.span("pipeline") as parent:
    with tracer.span("extract") as child1:
        data = extract(input)
    
    with tracer.span("transform") as child2:
        transformed = transform(data)
    
    with tracer.span("load") as child3:
        load(transformed)
```

### Автоматический трейсинг

```python
from rlm_toolkit.observability import create_tracer

# Авто-трейсинг всех RLM операций
tracer = create_tracer(
    service_name="my-app",
    auto_instrument=True,  # Трассировать все LLM вызовы
    sample_rate=0.1        # Сэмплировать 10% в production
)
```

## Контроль затрат

### Лимиты бюджета

```python
from rlm_toolkit.observability import CostTracker

tracker = CostTracker(
    budget_usd=50.0,
    alert_threshold=0.8,  # Алерт при 80%
    on_budget_exceeded=lambda: print("Бюджет превышен!")
)

# Автоматический учёт затрат
rlm = RLM.from_openai("gpt-4o", cost_tracker=tracker)

# Проверка статуса
if tracker.is_near_limit():
    print("Внимание: приближаемся к лимиту бюджета")
```

### Отчёты о затратах

```python
report = tracker.get_report()

print(f"""
Отчёт о затратах
----------------
Всего: ${report.total_cost:.4f}
По моделям:
  - gpt-4o: ${report.by_model['gpt-4o']:.4f}
  - gpt-3.5-turbo: ${report.by_model['gpt-3.5-turbo']:.4f}
По операциям:
  - completions: ${report.by_operation['completion']:.4f}
  - embeddings: ${report.by_operation['embedding']:.4f}
Остаток: ${report.remaining:.2f} ({report.remaining_percent:.1f}%)
""")
```

### Отслеживание по запросам

```python
# Отслеживаем конкретные операции
with tracker.track("expensive_analysis"):
    result = rlm.run(huge_document, "Детальный анализ")

# Получаем стоимость операции
op_cost = tracker.get_operation_cost("expensive_analysis")
print(f"Стоимость анализа: ${op_cost:.4f}")
```

## Экспортёры

### Langfuse

```python
from rlm_toolkit.observability import LangfuseExporter

exporter = LangfuseExporter(
    public_key="pk-...",
    secret_key="sk-...",
    host="https://cloud.langfuse.com"
)

tracer = Tracer(service_name="my-app", exporter=exporter)
```

### LangSmith

```python
from rlm_toolkit.observability import LangSmithExporter

exporter = LangSmithExporter(
    api_key="ls-...",
    project="my-project"
)

tracer = Tracer(service_name="my-app", exporter=exporter)
```

### Console (Разработка)

```python
from rlm_toolkit.observability import ConsoleExporter

# Красивый вывод трейсов в консоль
tracer = Tracer(
    service_name="my-app",
    exporter=ConsoleExporter(show_attributes=True)
)
```

### OpenTelemetry

```python
from rlm_toolkit.observability import Tracer
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Использование стандартного OTLP экспортёра
tracer = Tracer(
    service_name="my-app",
    exporter=OTLPSpanExporter(endpoint="localhost:4317")
)
```

## Production примеры

### Пример 1: API Сервис

```python
from fastapi import FastAPI
from rlm_toolkit import RLM
from rlm_toolkit.observability import Tracer, CostTracker, LangfuseExporter

app = FastAPI()

# Глобальная наблюдаемость
tracer = Tracer(
    service_name="api",
    exporter=LangfuseExporter(...)
)
cost_tracker = CostTracker(budget_usd=1000.0)
rlm = RLM.from_openai("gpt-4o", tracer=tracer, cost_tracker=cost_tracker)

@app.post("/analyze")
async def analyze(text: str):
    with tracer.span("api.analyze") as span:
        span.set_attribute("text_length", len(text))
        result = rlm.run(text, "Анализ тональности")
        return {"result": result.final_answer}

@app.get("/costs")
async def get_costs():
    return cost_tracker.get_report().to_dict()
```

### Пример 2: Пакетная обработка

```python
from rlm_toolkit.observability import CostTracker

tracker = CostTracker(budget_usd=100.0)
rlm = RLM.from_openai("gpt-4o", cost_tracker=tracker)

documents = load_documents()  # 1000 документов

for i, doc in enumerate(documents):
    # Обработка с защитой бюджета
    if tracker.is_near_limit():
        print(f"Остановка на документе {i}: лимит бюджета")
        break
    
    with tracker.track(f"doc_{i}"):
        rlm.run(doc, "Суммаризация")

print(f"Обработано {i} документов, общая стоимость: ${tracker.get_report().total_cost:.2f}")
```

## Связанное

- [Providers](providers.md)
- [Туториал: Первое приложение](../tutorials/01-first-app.md)
- [MCP Server](../mcp-server.md)
