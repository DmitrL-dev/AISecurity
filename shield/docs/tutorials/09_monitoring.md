# Tutorial 9: Monitoring & Observability

> **SSP Module 2.9**

---

## 🎯 Цель

Настроить полную observability для Shield:

- Prometheus metrics
- Grafana dashboards
- Alerting
- Logging best practices

---

## Шаг 1: Включение Prometheus

`monitoring_config.json`:

```json
{
  "version": "1.2.0",
  "name": "shield-monitored",

  "metrics": {
    "prometheus": {
      "enabled": true,
      "host": "0.0.0.0",
      "port": 9090,
      "path": "/metrics"
    }
  },

  "zones": [{ "name": "external", "trust_level": 1 }],

  "rules": [
    {
      "name": "block_injection",
      "pattern": "ignore.*previous",
      "action": "block"
    }
  ],

  "api": { "enabled": true, "port": 8080 }
}
```

---

## Шаг 2: Запуск и проверка

```bash
./shield -c monitoring_config.json
```

```bash
curl http://localhost:9090/metrics
```

```prometheus
# HELP shield_requests_total Total number of requests
# TYPE shield_requests_total counter
shield_requests_total{zone="external",action="allow"} 1523
shield_requests_total{zone="external",action="block"} 287

# HELP shield_request_duration_seconds Request processing time
# TYPE shield_request_duration_seconds histogram
shield_request_duration_seconds_bucket{le="0.001"} 1654
shield_request_duration_seconds_bucket{le="0.005"} 1798
shield_request_duration_seconds_bucket{le="0.01"} 1810

# HELP shield_threat_score Current threat score distribution
# TYPE shield_threat_score histogram
shield_threat_score_bucket{zone="external",le="0.1"} 1523
shield_threat_score_bucket{zone="external",le="0.5"} 1650
shield_threat_score_bucket{zone="external",le="0.9"} 1810

# HELP shield_rules_matched_total Rules matched by name
# TYPE shield_rules_matched_total counter
shield_rules_matched_total{rule="block_injection"} 287

# HELP shield_active_sessions Current active sessions
# TYPE shield_active_sessions gauge
shield_active_sessions{zone="external"} 42

# HELP shield_uptime_seconds Shield uptime
# TYPE shield_uptime_seconds counter
shield_uptime_seconds 3600
```

---

## Шаг 3: Prometheus Configuration

`prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "shield"
    static_configs:
      - targets: ["localhost:9090"]

  - job_name: "shield-ha-node1"
    static_configs:
      - targets: ["192.168.1.1:9090"]
        labels:
          node: "primary"

  - job_name: "shield-ha-node2"
    static_configs:
      - targets: ["192.168.1.2:9090"]
        labels:
          node: "standby"
```

```bash
prometheus --config.file=prometheus.yml
```

---

## Шаг 4: Key Metrics

| Metric                            | Type      | Description                     |
| --------------------------------- | --------- | ------------------------------- |
| `shield_requests_total`           | Counter   | Total requests by zone/action   |
| `shield_request_duration_seconds` | Histogram | Processing latency              |
| `shield_threat_score`             | Histogram | Threat score distribution       |
| `shield_rules_matched_total`      | Counter   | Rules matched                   |
| `shield_blocked_total`            | Counter   | Blocked requests                |
| `shield_active_sessions`          | Gauge     | Current sessions                |
| `shield_ha_state`                 | Gauge     | HA state (1=primary, 0=standby) |

---

## Шаг 5: Grafana Dashboard

### Импорт

1. Открой Grafana: http://localhost:3000
2. Dashboards → Import
3. Upload `shield_dashboard.json` или используй ID

### Panels

**Request Rate:**

```promql
rate(shield_requests_total[5m])
```

**Block Rate:**

```promql
rate(shield_requests_total{action="block"}[5m]) / rate(shield_requests_total[5m]) * 100
```

**Latency P99:**

```promql
histogram_quantile(0.99, rate(shield_request_duration_seconds_bucket[5m]))
```

**Threat Score Distribution:**

```promql
histogram_quantile(0.9, rate(shield_threat_score_bucket[5m]))
```

**Top Blocked Rules:**

```promql
topk(5, rate(shield_rules_matched_total[1h]))
```

---

## Шаг 6: Alerting Rules

`alert_rules.yml`:

```yaml
groups:
  - name: shield
    rules:
      - alert: ShieldHighBlockRate
        expr: |
          rate(shield_requests_total{action="block"}[5m]) 
          / rate(shield_requests_total[5m]) > 0.3
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High block rate detected"
          description: "Block rate is {{ $value | humanizePercentage }}"

      - alert: ShieldHighLatency
        expr: |
          histogram_quantile(0.99, rate(shield_request_duration_seconds_bucket[5m])) > 0.01
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "P99 latency is {{ $value }}s"

      - alert: ShieldDown
        expr: up{job="shield"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Shield is down"
          description: "Shield instance {{ $labels.instance }} is down"

      - alert: ShieldHAFailover
        expr: changes(shield_ha_state[5m]) > 0
        labels:
          severity: warning
        annotations:
          summary: "HA failover detected"
          description: "Shield HA state changed"
```

---

## Шаг 7: Logging

### Конфигурация

```json
{
  "logging": {
    "level": "info",
    "format": "json",
    "output": {
      "file": {
        "enabled": true,
        "path": "/var/log/shield/shield.log",
        "max_size_mb": 100,
        "max_files": 10
      },
      "stdout": {
        "enabled": true
      }
    }
  }
}
```

### Log Levels

| Level   | Description        | Example                  |
| ------- | ------------------ | ------------------------ |
| `debug` | Verbose debugging  | Pattern matching details |
| `info`  | Normal operations  | Request allowed/blocked  |
| `warn`  | Warning conditions | High threat score        |
| `error` | Errors             | Config parse failure     |
| `fatal` | Critical failures  | Cannot bind port         |

### JSON Log Format

```json
{
  "timestamp": "2026-01-02T09:15:00.123Z",
  "level": "info",
  "event": "request_evaluated",
  "zone": "external",
  "action": "block",
  "threat_score": 0.9,
  "matched_rules": ["block_injection"],
  "processing_time_ms": 0.45,
  "session_id": "sess-123",
  "input_hash": "abc123"
}
```

---

## Шаг 8: Log Aggregation (ELK)

### Filebeat config

```yaml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/shield/*.log
    json.keys_under_root: true
    json.add_error_key: true

output.elasticsearch:
  hosts: ["localhost:9200"]
  index: "shield-%{+yyyy.MM.dd}"
```

### Kibana Queries

```
# All blocked requests
action: "block"

# High threat scores
threat_score >= 0.8

# Specific rule
matched_rules: "block_injection"

# Slow requests
processing_time_ms > 10
```

---

## Шаг 9: C Integration

```c
#include "sentinel_shield.h"

int main(void) {
    shield_context_t ctx;
    shield_init(&ctx);
    shield_load_config(&ctx, "monitoring_config.json");

    // Получить текущие метрики
    shield_metrics_t metrics;
    shield_get_metrics(&ctx, &metrics);

    printf("=== Shield Metrics ===\n");
    printf("Total requests: %lu\n", metrics.total_requests);
    printf("Blocked: %lu (%.1f%%)\n",
           metrics.blocked_requests,
           100.0 * metrics.blocked_requests / metrics.total_requests);
    printf("Avg latency: %.2fms\n", metrics.avg_latency_ms);
    printf("P99 latency: %.2fms\n", metrics.p99_latency_ms);
    printf("Active sessions: %d\n", metrics.active_sessions);

    // Custom metric
    shield_metric_inc(&ctx, "custom_counter", 1);
    shield_metric_set(&ctx, "custom_gauge", 42.5);

    shield_destroy(&ctx);
    return 0;
}
```

---

## Шаг 10: CLI Monitoring Commands

```bash
Shield> show metrics

╔══════════════════════════════════════════════════════════╗
║                    SHIELD METRICS                         ║
╚══════════════════════════════════════════════════════════╝

Requests:
  Total: 15,234
  Allowed: 12,187 (80.0%)
  Blocked: 3,047 (20.0%)

Performance:
  Avg latency: 0.42ms
  P50 latency: 0.28ms
  P99 latency: 1.23ms

Top Blocked Rules:
  1. block_injection: 1,892
  2. block_jailbreak: 845
  3. block_extraction: 310

Sessions:
  Active: 127
  Peak (24h): 342

Shield> show metrics --format prometheus
# Output in Prometheus format
```

---

## 🎉 Что ты узнал

- ✅ Prometheus metrics endpoint
- ✅ Key metrics to monitor
- ✅ Grafana dashboards
- ✅ Alert rules
- ✅ JSON logging
- ✅ Log aggregation

---

## Следующий tutorial

**Tutorial 10:** Red Team Testing — Тестирование защиты

---

_"You can't improve what you don't measure."_
