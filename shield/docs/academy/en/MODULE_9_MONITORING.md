# SENTINEL Academy — Module 9

## Monitoring & Observability

_SSP Level | Duration: 3 hours_

---

## Prometheus Metrics

Enable metrics:

```
Shield(config)# metrics enable
Shield(config)# metrics port 9090
```

### Key Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `shield_requests_total` | Counter | Total requests |
| `shield_blocked_total` | Counter | Blocked requests |
| `shield_latency_seconds` | Histogram | Evaluation latency |
| `shield_active_sessions` | Gauge | Active sessions |

---

## Grafana Dashboards

Included dashboards:
- Shield Overview
- Guard Performance
- Zone Traffic
- Threat Detection

---

## Logging

```
Shield(config)# logging level info
Shield(config)# logging host 192.168.1.100
Shield(config)# logging buffered 8192
```

### Log Levels

| Level | Use |
|-------|-----|
| debug | Development |
| info | Production |
| warn | Alerts only |
| error | Errors only |

---

## SIEM Integration

```
Shield(config)# siem enable
Shield(config)# siem destination splunk.company.com 514
Shield(config)# siem format cef
```

Formats: CEF, JSON, Syslog

---

## Alerting

```
Shield(config)# alert destination webhook https://...
Shield(config)# alert threshold critical
```

---

_"You can't protect what you can't see."_
