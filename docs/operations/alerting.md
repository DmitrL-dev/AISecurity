# 🚨 SENTINEL Alerting Guide

> **Purpose:** Alert rules, escalation procedures, on-call response  
> **Stack:** Prometheus Alertmanager / PagerDuty / Slack

---

## Alert Rules

### Critical Alerts (P1 — Immediate Response)

```yaml
# prometheus-rules.yaml
groups:
  - name: sentinel-critical
    rules:
      # Brain service down
      - alert: SentinelBrainDown
        expr: sentinel_brain_up == 0
        for: 1m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "SENTINEL Brain is DOWN"
          description: "Brain service has been down for >1 minute. All analysis is failing."
          runbook: "https://docs.sentinel.io/runbooks/brain-down"

      # Gateway down
      - alert: SentinelGatewayDown
        expr: up{job="sentinel-gateway"} == 0
        for: 1m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "SENTINEL Gateway is DOWN"
          description: "Gateway service is unreachable."
          runbook: "https://docs.sentinel.io/runbooks/gateway-down"

      # High error rate
      - alert: SentinelHighErrorRate
        expr: |
          rate(sentinel_requests_total{status="error"}[5m]) 
          / rate(sentinel_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "SENTINEL error rate >5%"
          description: "Error rate is {{ $value | humanizePercentage }}"
          runbook: "https://docs.sentinel.io/runbooks/high-error-rate"
```

### Warning Alerts (P2 — Respond within 1 hour)

```yaml
# High latency
- alert: SentinelHighLatency
  expr: |
    histogram_quantile(0.95, 
      rate(sentinel_analysis_duration_seconds_bucket[5m])
    ) > 0.5
  for: 10m
  labels:
    severity: warning
    team: platform
  annotations:
    summary: "SENTINEL p95 latency >500ms"
    description: "p95 latency is {{ $value | humanizeDuration }}"
    runbook: "https://docs.sentinel.io/runbooks/high-latency"

# Redis connection issues
- alert: SentinelRedisUnhealthy
  expr: sentinel_redis_connected == 0
  for: 5m
  labels:
    severity: warning
    team: platform
  annotations:
    summary: "SENTINEL cannot connect to Redis"
    runbook: "https://docs.sentinel.io/runbooks/redis-issues"

# High block rate (possible attack or misconfiguration)
- alert: SentinelHighBlockRate
  expr: |
    rate(sentinel_requests_total{status="blocked"}[5m]) 
    / rate(sentinel_requests_total[5m]) > 0.2
  for: 15m
  labels:
    severity: warning
    team: security
  annotations:
    summary: "SENTINEL block rate >20%"
    description: "Unusual block rate. Possible attack or threshold misconfiguration."
```

### Info Alerts (P3 — Review next business day)

```yaml
# Low traffic
- alert: SentinelLowTraffic
  expr: rate(sentinel_requests_total[1h]) < 1
  for: 1h
  labels:
    severity: info
    team: platform
  annotations:
    summary: "SENTINEL low traffic"
    description: "Less than 1 req/sec for 1 hour. Check if expected."

# Cache hit rate low
- alert: SentinelLowCacheHitRate
  expr: |
    sentinel_cache_hits 
    / (sentinel_cache_hits + sentinel_cache_misses) < 0.5
  for: 30m
  labels:
    severity: info
    team: platform
  annotations:
    summary: "SENTINEL cache hit rate <50%"
    description: "Consider increasing cache TTL or size."
```

---

## Alertmanager Configuration

```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m
  slack_api_url: "https://hooks.slack.com/services/XXXXX"
  pagerduty_url: "https://events.pagerduty.com/v2/enqueue"

route:
  receiver: "default"
  group_by: ["alertname", "severity"]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

  routes:
    # Critical → PagerDuty + Slack
    - match:
        severity: critical
      receiver: "critical-alerts"
      continue: true

    # Warning → Slack only
    - match:
        severity: warning
      receiver: "warning-alerts"

    # Security team
    - match:
        team: security
      receiver: "security-alerts"

receivers:
  - name: "default"
    slack_configs:
      - channel: "#sentinel-alerts"
        send_resolved: true

  - name: "critical-alerts"
    pagerduty_configs:
      - service_key: "YOUR_PAGERDUTY_KEY"
        severity: critical
    slack_configs:
      - channel: "#sentinel-critical"
        send_resolved: true

  - name: "warning-alerts"
    slack_configs:
      - channel: "#sentinel-alerts"
        send_resolved: true

  - name: "security-alerts"
    slack_configs:
      - channel: "#security-alerts"
        send_resolved: true

inhibit_rules:
  # If Brain is down, suppress high error rate alert
  - source_match:
      alertname: "SentinelBrainDown"
    target_match:
      alertname: "SentinelHighErrorRate"
    equal: ["team"]
```

---

## Escalation Matrix

| Severity        | Response Time     | Notification              | Escalation          |
| --------------- | ----------------- | ------------------------- | ------------------- |
| **P1 Critical** | 5 minutes         | PagerDuty + Slack + Phone | Manager after 15min |
| **P2 Warning**  | 1 hour            | Slack                     | Lead after 2 hours  |
| **P3 Info**     | Next business day | Slack                     | —                   |

---

## On-Call Responsibilities

### When Paged

1. **Acknowledge** within 5 minutes
2. **Assess** severity and impact
3. **Mitigate** (rollback, scale, restart)
4. **Communicate** status in Slack
5. **Document** in incident log
6. **Post-mortem** for P1/P2

### Handoff Template

```
## Shift Handoff - SENTINEL

**Date:** YYYY-MM-DD
**From:** @engineer1
**To:** @engineer2

### Open Issues
- [ ] SentinelHighLatency - investigating, likely Redis

### Recent Changes
- Deployed v1.2.3 at 14:00 UTC
- Updated thresholds for injection engine

### Upcoming
- Maintenance window Saturday 02:00-04:00 UTC

### Notes
- Redis cluster node redis-3 showing high memory, watching
```

---

## Silencing Alerts

### Planned Maintenance

```bash
# Create silence for 2 hours
curl -X POST http://alertmanager:9093/api/v2/silences \
  -H "Content-Type: application/json" \
  -d '{
    "matchers": [
      {"name": "job", "value": "sentinel", "isRegex": false}
    ],
    "startsAt": "2024-12-14T02:00:00Z",
    "endsAt": "2024-12-14T04:00:00Z",
    "createdBy": "admin",
    "comment": "Scheduled maintenance"
  }'
```

### False Positive

```bash
# Silence specific alert for 1 day
curl -X POST http://alertmanager:9093/api/v2/silences \
  -d '{
    "matchers": [
      {"name": "alertname", "value": "SentinelLowTraffic"}
    ],
    "endsAt": "2024-12-15T00:00:00Z",
    "comment": "Weekend low traffic expected"
  }'
```
