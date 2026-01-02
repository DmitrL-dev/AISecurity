# SENTINEL Academy — Module 9

## Monitoring & Observability

_SSP Level | Время: 4 часа_

---

## Введение

"You can't improve what you don't measure."

В этом модуле — полная observability для Shield.

---

## 9.1 Three Pillars of Observability

### Metrics

**What:** Числовые измерения состояния системы.

```prometheus
shield_requests_total{zone="external",action="allow"} 15234
```

### Logs

**What:** Записи о событиях с контекстом.

```json
{
  "level": "info",
  "event": "blocked",
  "rule": "injection",
  "input_hash": "abc123"
}
```

### Traces

**What:** Путь запроса через систему.

```
[trace-id: abc] → API → Guard → Rule Engine → Response
```

---

## 9.2 Prometheus Metrics

### Configuration

```json
{
  "metrics": {
    "prometheus": {
      "enabled": true,
      "host": "0.0.0.0",
      "port": 9090,
      "path": "/metrics",
      "namespace": "shield"
    }
  }
}
```

### Built-in Metrics

#### Counters

```prometheus
# Requests by zone and action
shield_requests_total{zone="external",action="allow"} 15234
shield_requests_total{zone="external",action="block"} 2847

# Rule matches
shield_rules_matched_total{rule="block_injection"} 2100

# Guard evaluations
shield_guard_evaluations_total{guard="llm",result="block"} 847
```

#### Gauges

```prometheus
# Active sessions
shield_active_sessions{zone="external"} 127

# HA state
shield_ha_is_primary 1

# Loaded rules
shield_rules_loaded 35
```

#### Histograms

```prometheus
# Request latency
shield_request_duration_seconds_bucket{le="0.001"} 12345
shield_request_duration_seconds_bucket{le="0.005"} 14000
shield_request_duration_seconds_bucket{le="0.01"} 15000

# Threat score distribution
shield_threat_score_bucket{le="0.1"} 14000
shield_threat_score_bucket{le="0.5"} 14800
shield_threat_score_bucket{le="0.9"} 15000
```

---

## 9.3 Key Metrics Dashboard

### Essential Panels

| Panel           | Query                                                                               | Purpose                |
| --------------- | ----------------------------------------------------------------------------------- | ---------------------- |
| Request Rate    | `rate(shield_requests_total[5m])`                                                   | Throughput             |
| Block Rate      | `rate(shield_requests_total{action="block"}[5m]) / rate(shield_requests_total[5m])` | Security effectiveness |
| P99 Latency     | `histogram_quantile(0.99, rate(shield_request_duration_seconds_bucket[5m]))`        | Performance            |
| Error Rate      | `rate(shield_errors_total[5m])`                                                     | Health                 |
| Active Sessions | `shield_active_sessions`                                                            | Load                   |

### Grafana Dashboard JSON

```json
{
  "panels": [
    {
      "title": "Request Rate",
      "type": "graph",
      "targets": [
        {
          "expr": "rate(shield_requests_total[5m])",
          "legendFormat": "{{zone}} - {{action}}"
        }
      ]
    },
    {
      "title": "Block Rate %",
      "type": "gauge",
      "targets": [
        {
          "expr": "sum(rate(shield_requests_total{action='block'}[5m])) / sum(rate(shield_requests_total[5m])) * 100"
        }
      ]
    },
    {
      "title": "Latency Heatmap",
      "type": "heatmap",
      "targets": [
        {
          "expr": "rate(shield_request_duration_seconds_bucket[5m])"
        }
      ]
    }
  ]
}
```

---

## 9.4 Alerting

### Alert Rules

```yaml
groups:
  - name: shield_alerts
    rules:
      # High block rate
      - alert: ShieldHighBlockRate
        expr: |
          sum(rate(shield_requests_total{action="block"}[5m])) / 
          sum(rate(shield_requests_total[5m])) > 0.3
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Block rate above 30%"
          description: "Current: {{ $value | humanizePercentage }}"

      # High latency
      - alert: ShieldHighLatency
        expr: |
          histogram_quantile(0.99, 
            rate(shield_request_duration_seconds_bucket[5m])) > 0.01
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P99 latency above 10ms"
          description: "Current: {{ $value | humanizeDuration }}"

      # Shield down
      - alert: ShieldDown
        expr: up{job="shield"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Shield instance down"

      # HA failover
      - alert: ShieldHAFailover
        expr: changes(shield_ha_is_primary[5m]) > 0
        labels:
          severity: warning
        annotations:
          summary: "HA failover occurred"

      # No recent blocks (anomaly)
      - alert: ShieldNoBlocks
        expr: |
          rate(shield_requests_total{action="block"}[1h]) == 0 
          and rate(shield_requests_total[1h]) > 0
        for: 1h
        labels:
          severity: info
        annotations:
          summary: "No blocks in 1 hour - verify rules"
```

---

## 9.5 Logging

### Configuration

```json
{
  "logging": {
    "level": "info",
    "format": "json",

    "outputs": [
      {
        "type": "stdout",
        "enabled": true
      },
      {
        "type": "file",
        "enabled": true,
        "path": "/var/log/shield/shield.log",
        "rotation": {
          "max_size_mb": 100,
          "max_files": 10,
          "compress": true
        }
      }
    ],

    "fields": {
      "service": "shield",
      "environment": "production"
    },

    "sampling": {
      "enabled": true,
      "rate": 0.1
    }
  }
}
```

### Log Levels

| Level   | Use                      |
| ------- | ------------------------ |
| `debug` | Development only         |
| `info`  | Normal operations        |
| `warn`  | Issues needing attention |
| `error` | Failures                 |
| `fatal` | Critical failures        |

### Structured Log Format

```json
{
  "timestamp": "2026-01-02T09:30:00.123Z",
  "level": "info",
  "logger": "shield.guard.llm",
  "message": "Request blocked",
  "fields": {
    "zone": "external",
    "action": "block",
    "rule": "block_injection",
    "threat_score": 0.95,
    "processing_time_ms": 0.45,
    "session_id": "sess-abc123",
    "input_hash": "sha256:abc..."
  }
}
```

### Log Aggregation

**Filebeat → Elasticsearch:**

```yaml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/shield/*.log
    json.keys_under_root: true
    json.overwrite_keys: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "shield-%{+yyyy.MM.dd}"
```

---

## 9.6 Distributed Tracing

### Configuration

```json
{
  "tracing": {
    "enabled": true,
    "provider": "jaeger",
    "endpoint": "http://jaeger:14268/api/traces",
    "sample_rate": 0.1,
    "service_name": "shield"
  }
}
```

### Span Hierarchy

```
[shield:evaluate] ─────────────────────────────────────
    ├── [shield:parse_request] ────
    ├── [shield:pattern_match] ───────────
    ├── [shield:semantic_analysis] ──────────────────
    ├── [shield:guard:llm] ────────────
    └── [shield:build_response] ──
```

### C API

```c
#include "tracing.h"

void handle_request(const char *input) {
    // Start span
    span_t *span = span_start("shield:evaluate");
    span_set_tag(span, "zone", "external");

    // Child span
    span_t *child = span_start_child(span, "shield:guard:llm");
    // ... guard evaluation ...
    span_finish(child);

    span_finish(span);
}
```

---

## 9.7 Custom Metrics

### C API

```c
#include "metrics.h"

// Counter
metric_counter_t *requests;
metric_counter_create("custom_requests_total", "Custom request counter", &requests);
metric_counter_inc(requests, labels);

// Gauge
metric_gauge_t *active;
metric_gauge_create("custom_active", "Active items", &active);
metric_gauge_set(active, 42.5, labels);

// Histogram
metric_histogram_t *latency;
double buckets[] = {0.001, 0.005, 0.01, 0.05, 0.1};
metric_histogram_create("custom_latency", "Custom latency", buckets, 5, &latency);
metric_histogram_observe(latency, 0.003, labels);
```

---

## 9.8 CLI Monitoring

```bash
Shield> show metrics

╔══════════════════════════════════════════════════════════╗
║                    SHIELD METRICS                         ║
╚══════════════════════════════════════════════════════════╝

Requests (last 5m):
  Total: 15,234
  Allowed: 12,387 (81.3%)
  Blocked: 2,847 (18.7%)

Performance:
  Avg latency: 0.42ms
  P50: 0.28ms
  P99: 1.23ms
  Max: 5.67ms

Top Rules:
  1. block_injection: 1,892 (66.5%)
  2. block_jailbreak: 645 (22.7%)
  3. block_extraction: 310 (10.9%)

Guards:
  LLM: 2,500 evaluations, 847 blocks
  RAG: 1,200 evaluations, 123 blocks

Sessions:
  Active: 127
  Peak (24h): 342

Shield> show metrics --live
     Requests/s  Block%  P99 Latency
09:30:00    23.4    18.2%     0.98ms
09:30:05    25.1    19.5%     1.12ms
09:30:10    22.8    17.9%     0.89ms
```

---

## 9.9 Health Checks

### Endpoints

**Basic:**

```bash
curl http://localhost:8080/health
```

```json
{ "status": "healthy" }
```

**Detailed:**

```bash
curl http://localhost:8080/health/detailed
```

```json
{
  "status": "healthy",
  "version": "1.2.0",
  "uptime_seconds": 86400,
  "components": {
    "api": { "status": "healthy" },
    "guards": { "status": "healthy", "loaded": 6 },
    "rules": { "status": "healthy", "loaded": 35 },
    "ha": { "status": "healthy", "role": "primary" }
  }
}
```

**Ready:**

```bash
curl http://localhost:8080/health/ready
```

For Kubernetes readiness probe.

---

## Практика

### Задание 1

Настрой Prometheus + Grafana:

- Скрапинг Shield metrics
- Dashboard с 5 основными panels

### Задание 2

Создай alert rules:

- Block rate > 40%
- P99 latency > 5ms
- Instance down

### Задание 3

Настрой JSON logging:

- Rotation 100MB
- 10 файлов
- Compression

---

## Итоги Module 9

- Metrics, Logs, Traces — три столпа
- Prometheus для метрик
- JSON structured logging
- Alerting для proactive monitoring
- CLI для quick checks

---

## Следующий модуль

**Module 10: Enterprise Deployment**

Production deployment best practices.

---

_"If you can't measure it, you can't improve it."_
