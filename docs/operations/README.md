# 🔧 SENTINEL Operations Documentation

> **Audience:** DevOps, SRE, System Administrators  
> **Purpose:** Production deployment, monitoring, incident response  
> **SLA Target:** 99.9% uptime, <100ms p95 latency

---

## Contents

| Document                                       | Purpose                                |
| ---------------------------------------------- | -------------------------------------- |
| [monitoring.md](./monitoring.md)               | Prometheus metrics, Grafana dashboards |
| [alerting.md](./alerting.md)                   | Alert rules, escalation procedures     |
| [capacity-planning.md](./capacity-planning.md) | Resource sizing, scaling guidelines    |
| [backup-restore.md](./backup-restore.md)       | Backup procedures, disaster recovery   |
| [upgrades.md](./upgrades.md)                   | Zero-downtime update procedures        |
| [runbooks/](./runbooks/)                       | Incident response playbooks            |

---

## Quick Reference

### Health Endpoints

| Endpoint            | Purpose              | Expected Response       |
| ------------------- | -------------------- | ----------------------- |
| `GET /health`       | Overall health       | `{"status": "healthy"}` |
| `GET /health/live`  | Kubernetes liveness  | `200 OK`                |
| `GET /health/ready` | Kubernetes readiness | `200 OK`                |
| `GET /metrics`      | Prometheus metrics   | Prometheus format       |

### Key Metrics

| Metric                               | Alert Threshold | Description            |
| ------------------------------------ | --------------- | ---------------------- |
| `sentinel_requests_total`            | —               | Total requests counter |
| `sentinel_requests_blocked`          | >10% of total   | Blocked requests       |
| `sentinel_analysis_duration_seconds` | p95 > 500ms     | Analysis latency       |
| `sentinel_error_rate`                | >1%             | Error rate             |
| `sentinel_brain_up`                  | 0               | Brain service status   |

### Default Ports

| Service         | Port  | Protocol   |
| --------------- | ----- | ---------- |
| Shield API      | 8081  | HTTP       |
| Shield Metrics  | 9090  | HTTP       |
| Brain API       | 8000  | HTTP       |
| Brain gRPC      | 50051 | gRPC       |
| Dashboard       | 3000  | HTTP       |
| Redis           | 6379  | TCP        |

---

## Architecture Overview

```
                    ┌─────────────────────────────────────────────────┐
                    │                LOAD BALANCER                     │
                    │              (TLS Termination)                   │
                    └─────────────────────────────────────────────────┘
                                          │
                    ╔═════════════════════╧═════════════════════╗
                    ║               SHIELD CLUSTER               ║
                    ║    (3+ replicas, DMZ gateway, stateless)   ║
                    ╚═════════════════════╤═════════════════════╝
                                          │ gRPC + mTLS
                    ╔═════════════════════╧═════════════════════╗
                    ║               BRAIN CLUSTER                ║
                    ║    (3+ replicas, 217 detection engines)    ║
                    ╚═════════════════════╤═════════════════════╝
                                          │
            ┌─────────────────────────────┼─────────────────────────────┐
            │                             │                             │
    ┌───────▼───────┐             ┌───────▼───────┐             ┌───────▼───────┐
    │     REDIS     │             │  PROMETHEUS   │             │      ELK      │
    │   (Cache)     │             │  (Metrics)    │             │   (Logs)      │
    └───────────────┘             └───────────────┘             └───────────────┘
```

---

## Operational Checklist

### Daily

- [ ] Check Grafana dashboard for anomalies
- [ ] Review blocked requests log
- [ ] Verify backup completion

### Weekly

- [ ] Review capacity trends
- [ ] Check for security updates
- [ ] Analyze false positive/negative rates

### Monthly

- [ ] Capacity planning review
- [ ] DR drill (restore from backup)
- [ ] Performance benchmark

---

## Emergency Contacts

| Role              | Responsibility             |
| ----------------- | -------------------------- |
| **On-Call SRE**   | First responder for alerts |
| **Security Team** | Attack pattern analysis    |
| **Platform Team** | Infrastructure issues      |

---

## Related Documentation

- [Deployment Guide](../guides/deployment.md)
- [Configuration Guide](../guides/configuration.md)
- [Engine Reference](../reference/engines.md)
