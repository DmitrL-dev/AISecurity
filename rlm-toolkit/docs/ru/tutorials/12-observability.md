# Туториал 12: Production Observability

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> Мониторинг, трейсинг и контроль затрат в production AI-приложениях

## Что вы изучите

- Настройка распределённого трейсинга
- Отслеживание и ограничение затрат LLM
- Интеграция с Langfuse
- Построение дашборда затрат

## Требования

```bash
pip install rlm-toolkit[observability]
```

---

## Часть 1: Базовый трейсинг

### 1.1 Console Tracer

```python
from rlm_toolkit import RLM
from rlm_toolkit.observability import Tracer, ConsoleExporter

# Создаём tracer с выводом в консоль
tracer = Tracer(
    service_name="my-ai-app",
    exporter=ConsoleExporter(show_attributes=True)
)

# Внедряем в RLM
rlm = RLM.from_openai("gpt-4o", tracer=tracer)

# Запуск — трейсы появляются в консоли
result = rlm.run("Объясни квантовые вычисления")
```

**Вывод консоли:**
```
[SPAN] rlm.run (1.24s)
  ├─ prompt_tokens: 15
  ├─ completion_tokens: 234
  └─ model: gpt-4o

[SPAN] embedding.create (0.12s)
  └─ dimensions: 1536
```

---

## Часть 2: Контроль затрат

### 2.1 Установка бюджета

```python
from rlm_toolkit.observability import CostTracker

tracker = CostTracker(
    budget_usd=10.0,
    alert_threshold=0.8  # Алерт при 80%
)

rlm = RLM.from_openai("gpt-4o", cost_tracker=tracker)

# Выполняем запросы
for i in range(100):
    if tracker.is_near_limit():
        print(f"⚠️ Предупреждение бюджета на запросе {i}")
        break
    rlm.run(f"Вопрос {i}")

# Финальный отчёт
report = tracker.get_report()
print(f"Всего потрачено: ${report.total_cost:.4f}")
```

### 2.2 Отслеживание по операциям

```python
# Отслеживаем конкретные дорогие операции
with tracker.track("heavy_analysis"):
    result = rlm.run(huge_document, "Детальный анализ")

print(f"Стоимость анализа: ${tracker.get_operation_cost('heavy_analysis'):.4f}")
```

---

## Часть 3: Интеграция с Langfuse

### 3.1 Настройка

```python
from rlm_toolkit.observability import LangfuseExporter

exporter = LangfuseExporter(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    host="https://cloud.langfuse.com"
)

tracer = Tracer(service_name="production-api", exporter=exporter)
rlm = RLM.from_openai("gpt-4o", tracer=tracer)
```

### 3.2 Просмотр в дашборде

1. Перейдите на cloud.langfuse.com
2. Откройте ваш проект
3. Смотрите все трейсы с латентностью, стоимостью, токенами

---

## Часть 4: Кастомные спаны

### 4.1 Ручная инструментация

```python
with tracer.span("data_pipeline") as parent:
    # Шаг 1: Загрузка
    with tracer.span("load_documents") as load_span:
        docs = load_all_documents()
        load_span.set_attribute("doc_count", len(docs))
    
    # Шаг 2: Обработка
    with tracer.span("process") as proc_span:
        for doc in docs:
            result = rlm.run(doc, "Суммаризация")
            proc_span.set_attribute("processed", True)
    
    # Шаг 3: Сохранение
    with tracer.span("save_results"):
        save_to_database(results)
```

---

## Часть 5: Production дашборд

### 5.1 FastAPI интеграция

```python
from fastapi import FastAPI
from rlm_toolkit import RLM
from rlm_toolkit.observability import Tracer, CostTracker, LangfuseExporter

app = FastAPI()

# Глобальная наблюдаемость
tracer = Tracer(service_name="api", exporter=LangfuseExporter(...))
cost_tracker = CostTracker(budget_usd=1000.0)
rlm = RLM.from_openai("gpt-4o", tracer=tracer, cost_tracker=cost_tracker)

@app.post("/analyze")
async def analyze(text: str):
    with tracer.span("api.analyze") as span:
        span.set_attribute("input_length", len(text))
        result = rlm.run(text, "Анализ")
        return {"result": result.final_answer}

@app.get("/metrics")
async def get_metrics():
    report = cost_tracker.get_report()
    return {
        "total_cost": report.total_cost,
        "remaining": report.remaining,
        "by_model": report.by_model
    }
```

---

## Результаты

| Метрика | До | После |
|---------|-----|-------|
| Видимость затрат | ❌ Нет | ✅ Real-time |
| Защита бюджета | ❌ Нет | ✅ Авто-стоп |
| Время дебага | 30 мин | 2 мин |

---

## Следующие шаги

- [Концепция: Observability](../concepts/observability.md)
- [Туториал: Callbacks](13-callbacks.md)
- [MCP Server](10-mcp-server.md)
