# 📊 Урок 2.4: Мониторинг и Observability

> **Время: 35 минут** | Mid-Level Модуль 2

---

## Три столпа

| Столп | Инструмент | Назначение |
|-------|------------|------------|
| **Метрики** | Prometheus | Числовые данные |
| **Логи** | ELK/Loki | Записи событий |
| **Трейсы** | Jaeger/Tempo | Поток запросов |

---

## Prometheus Метрики

```python
from prometheus_client import Counter, Histogram, start_http_server

# Определяем метрики
SCANS_TOTAL = Counter(
    'sentinel_scans_total',
    'Всего выполнено сканирований',
    ['engine', 'result']
)

SCAN_DURATION = Histogram(
    'sentinel_scan_duration_seconds',
    'Длительность сканирования в секундах',
    ['engine']
)

# Использование в коде
@SCAN_DURATION.labels(engine='injection').time()
def scan(text):
    result = detector.scan(text)
    SCANS_TOTAL.labels(
        engine='injection',
        result='threat' if result.is_threat else 'safe'
    ).inc()
    return result

# Экспорт метрик
start_http_server(9090)
```

---

## Grafana Dashboard

```json
{
  "panels": [
    {
      "title": "Сканирований в секунду",
      "type": "graph",
      "targets": [{
        "expr": "rate(sentinel_scans_total[5m])"
      }]
    },
    {
      "title": "Процент угроз",
      "type": "stat",
      "targets": [{
        "expr": "sum(rate(sentinel_scans_total{result='threat'}[1h])) / sum(rate(sentinel_scans_total[1h]))"
      }]
    }
  ]
}
```

---

## Структурированное логирование

```python
import structlog

logger = structlog.get_logger()

def scan_with_logging(text: str):
    log = logger.bind(
        request_id=generate_id(),
        text_length=len(text)
    )
    
    log.info("scan_started")
    
    result = detector.scan(text)
    
    log.info(
        "scan_completed",
        is_threat=result.is_threat,
        confidence=result.confidence,
        duration_ms=result.duration * 1000
    )
    
    return result
```

---

## OpenTelemetry Трейсинг

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

tracer = trace.get_tracer(__name__)

def scan_with_tracing(text: str):
    with tracer.start_as_current_span("sentinel.scan") as span:
        span.set_attribute("text.length", len(text))
        
        with tracer.start_as_current_span("tier1.scan"):
            tier1_result = tier1_scan(text)
        
        with tracer.start_as_current_span("tier2.scan"):
            tier2_result = tier2_scan(text)
        
        span.set_attribute("result.is_threat", result.is_threat)
        return result
```

---

## Правила алертинга

```yaml
# prometheus/alerts.yml
groups:
  - name: sentinel
    rules:
      - alert: HighThreatRate
        expr: rate(sentinel_scans_total{result="threat"}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Высокий процент обнаружения угроз"
          
      - alert: ScanLatencyHigh
        expr: histogram_quantile(0.99, sentinel_scan_duration_seconds) > 0.5
        for: 5m
        labels:
          severity: critical
```

---

## Ключевые выводы

1. **Три столпа** — метрики, логи, трейсы
2. **Prometheus** — для числовых метрик
3. **Структурированное логирование** — для поиска событий
4. **OpenTelemetry** — для распределённого трейсинга
5. **Алертинг** — проактивное реагирование

---

## Следующий урок

→ [3.1: Кастомные движки](./09-custom-engines.md)
