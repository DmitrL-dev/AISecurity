# 📊 Lesson 2.4: Monitoring & Observability

> **Time: 35 minutes** | Mid-Level Module 2

---

## The Three Pillars

| Pillar | Tool | Purpose |
|--------|------|---------|
| **Metrics** | Prometheus | Numerical data |
| **Logs** | ELK/Loki | Event records |
| **Traces** | Jaeger/Tempo | Request flow |

---

## Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, start_http_server

# Define metrics
SCANS_TOTAL = Counter(
    'sentinel_scans_total',
    'Total scans performed',
    ['engine', 'result']
)

SCAN_DURATION = Histogram(
    'sentinel_scan_duration_seconds',
    'Scan duration in seconds',
    ['engine']
)

# Use in code
@SCAN_DURATION.labels(engine='injection').time()
def scan(text):
    result = detector.scan(text)
    SCANS_TOTAL.labels(
        engine='injection',
        result='threat' if result.is_threat else 'safe'
    ).inc()
    return result

# Expose metrics
start_http_server(9090)
```

---

## Grafana Dashboard

```json
{
  "panels": [
    {
      "title": "Scans per Second",
      "type": "graph",
      "targets": [{
        "expr": "rate(sentinel_scans_total[5m])"
      }]
    },
    {
      "title": "Threat Detection Rate",
      "type": "stat",
      "targets": [{
        "expr": "sum(rate(sentinel_scans_total{result='threat'}[1h])) / sum(rate(sentinel_scans_total[1h]))"
      }]
    }
  ]
}
```

---

## Structured Logging

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

## OpenTelemetry Tracing

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

## Alerting Rules

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
          summary: "High threat detection rate"
          
      - alert: ScanLatencyHigh
        expr: histogram_quantile(0.99, sentinel_scan_duration_seconds) > 0.5
        for: 5m
        labels:
          severity: critical
```

---

## Key Takeaways

1. **Three pillars** — metrics, logs, traces
2. **Prometheus** — for numerical metrics
3. **Structured logging** — for searchable events
4. **OpenTelemetry** — for distributed tracing
5. **Alerting** — proactive incident response

---

## Next Lesson

→ [3.1: Custom Engines](./09-custom-engines.md)
