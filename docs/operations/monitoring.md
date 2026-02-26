# 📊 SENTINEL Monitoring Guide

> **Purpose:** Prometheus metrics, Grafana dashboards, observability  
> **Stack:** Prometheus + Grafana + OpenTelemetry

---

## Prometheus Metrics

### Request Metrics

```promql
# Total requests (counter)
sentinel_requests_total{status="success|blocked|error"}

# Request rate (per second)
rate(sentinel_requests_total[5m])

# Block rate (percentage)
rate(sentinel_requests_total{status="blocked"}[5m]) / rate(sentinel_requests_total[5m]) * 100
```

### Latency Metrics

```promql
# Analysis duration histogram
sentinel_analysis_duration_seconds_bucket{engine="all"}

# p50 latency
histogram_quantile(0.5, rate(sentinel_analysis_duration_seconds_bucket[5m]))

# p95 latency
histogram_quantile(0.95, rate(sentinel_analysis_duration_seconds_bucket[5m]))

# p99 latency
histogram_quantile(0.99, rate(sentinel_analysis_duration_seconds_bucket[5m]))
```

### Engine Metrics

```promql
# Engines triggered per request
sentinel_engines_triggered{engine="injection|behavioral|pii|..."}

# Top 5 triggered engines
topk(5, sum by (engine) (rate(sentinel_engines_triggered[5m])))

# Engine execution time
sentinel_engine_duration_seconds{engine="..."}
```

### System Metrics

```promql
# Brain service status (1=up, 0=down)
sentinel_brain_up

# Redis connection status
sentinel_redis_connected

# Active connections
sentinel_active_connections

# Cache hit rate
sentinel_cache_hits / (sentinel_cache_hits + sentinel_cache_misses) * 100
```

---

## Grafana Dashboard

### Import Dashboard

1. Open Grafana → Dashboards → Import
2. Upload `sentinel-dashboard.json` or use Dashboard ID: `SENTINEL-001`

### Key Panels

| Panel            | Query                               | Purpose                |
| ---------------- | ----------------------------------- | ---------------------- |
| **Request Rate** | `rate(sentinel_requests_total[5m])` | Traffic volume         |
| **Block Rate %** | `blocked / total * 100`             | Security effectiveness |
| **p95 Latency**  | `histogram_quantile(0.95, ...)`     | Performance SLA        |
| **Error Rate**   | `rate(error) / rate(total)`         | Reliability            |
| **Top Engines**  | `topk(10, engines_triggered)`       | Attack patterns        |

### Dashboard JSON

```json
{
  "title": "SENTINEL Overview",
  "uid": "sentinel-main",
  "panels": [
    {
      "title": "Requests per Second",
      "type": "timeseries",
      "targets": [
        {
          "expr": "sum(rate(sentinel_requests_total[5m])) by (status)",
          "legendFormat": "{{status}}"
        }
      ]
    },
    {
      "title": "p95 Latency",
      "type": "timeseries",
      "targets": [
        {
          "expr": "histogram_quantile(0.95, sum(rate(sentinel_analysis_duration_seconds_bucket[5m])) by (le))",
          "legendFormat": "p95"
        }
      ]
    },
    {
      "title": "Block Rate",
      "type": "gauge",
      "targets": [
        {
          "expr": "sum(rate(sentinel_requests_total{status=\"blocked\"}[5m])) / sum(rate(sentinel_requests_total[5m])) * 100"
        }
      ],
      "thresholds": {
        "steps": [
          { "color": "green", "value": 0 },
          { "color": "yellow", "value": 5 },
          { "color": "red", "value": 15 }
        ]
      }
    },
    {
      "title": "Top Triggered Engines",
      "type": "piechart",
      "targets": [
        {
          "expr": "topk(10, sum by (engine) (rate(sentinel_engines_triggered[1h])))"
        }
      ]
    }
  ]
}
```

---

## OpenTelemetry Integration

### Configuration

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

exporters:
  prometheus:
    endpoint: "0.0.0.0:9090"
  jaeger:
    endpoint: jaeger:14250
    tls:
      insecure: true

processors:
  batch:
    timeout: 10s

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [jaeger]
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [prometheus]
```

### SENTINEL Configuration

```env
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
OTEL_SERVICE_NAME=sentinel
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1  # 10% sampling
```

---

## Key SLIs/SLOs

| SLI                | SLO Target         | Measurement                     |
| ------------------ | ------------------ | ------------------------------- |
| **Availability**   | 99.9%              | `up{job="sentinel"} == 1`       |
| **Latency (p95)**  | <100ms             | `histogram_quantile(0.95, ...)` |
| **Error Rate**     | <0.1%              | `errors / total`                |
| **Block Accuracy** | >95% true positive | Manual review sample            |

---

## Prometheus Scrape Config

```yaml
# prometheus.yml
scrape_configs:
  - job_name: "sentinel-gateway"
    static_configs:
      - targets: ["gateway:8080"]
    metrics_path: /metrics
    scrape_interval: 15s

  - job_name: "sentinel-brain"
    static_configs:
      - targets: ["brain:50051"]
    metrics_path: /metrics
    scrape_interval: 15s
```

---

## Troubleshooting

### No Metrics

```bash
# Check metrics endpoint
curl http://localhost:8080/metrics

# Verify Prometheus target
curl http://prometheus:9090/api/v1/targets
```

### High Cardinality

```promql
# Check cardinality
count by (__name__) ({__name__=~"sentinel_.*"})

# Limit labels if needed
```
