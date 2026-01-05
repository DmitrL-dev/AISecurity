# SENTINEL Academy — Module 9

## Monitoring & Observability

_SSP Level | Duration: 4 hours_

---

## Introduction

"You can't improve what you don't measure."

In this module — complete observability for Shield.

---

## 9.1 Three Pillars of Observability

### Metrics

**What:** Numerical measurements of system state.

```prometheus
shield_requests_total{zone="external",action="allow"} 15234
```

### Logs

**What:** Event records with context.

```json
{
  "level": "info",
  "event": "blocked",
  "rule": "injection",
  "input_hash": "abc123"
}
```

### Traces

**What:** Request path through the system.

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
```

---

## 9.3 Key Metrics Dashboard

### Essential Panels

| Panel | Query | Purpose |
|-------|-------|---------|
| Request Rate | `rate(shield_requests_total[5m])` | Throughput |
| Block Rate | `rate(shield_requests_total{action="block"}[5m]) / rate(shield_requests_total[5m])` | Security effectiveness |
| P99 Latency | `histogram_quantile(0.99, rate(shield_request_duration_seconds_bucket[5m]))` | Performance |
| Error Rate | `rate(shield_errors_total[5m])` | Health |

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

      # Shield down
      - alert: ShieldDown
        expr: up{job="shield"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Shield instance down"
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
    ]
  }
}
```

### Log Levels

| Level | Use |
|-------|-----|
| `debug` | Development only |
| `info` | Normal operations |
| `warn` | Issues needing attention |
| `error` | Failures |
| `fatal` | Critical failures |

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

---

## 9.7 CLI Monitoring

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
```

---

## 9.8 Health Checks

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

---

## Practice

### Task 1

Configure Prometheus + Grafana:
- Scrape Shield metrics
- Dashboard with 5 main panels

### Task 2

Create alert rules:
- Block rate > 40%
- P99 latency > 5ms
- Instance down

### Task 3

Configure JSON logging:
- Rotation 100MB
- 10 files
- Compression

---

## Module 9 Summary

- Metrics, Logs, Traces — three pillars
- Prometheus for metrics
- JSON structured logging
- Alerting for proactive monitoring
- CLI for quick checks

---

## Next Module

**Module 10: Enterprise Deployment**

Production deployment best practices.

---

_"If you can't measure it, you can't improve it."_
