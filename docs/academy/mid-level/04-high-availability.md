# 🔄 Урок 1.4: High Availability

> **Время: 25 минут** | Mid-Level Module 1

---

## HA Patterns

### Active-Active

```
┌─────────────────────────────────────────────────────────────┐
│                      Load Balancer                          │
│                           │                                  │
│         ┌─────────────────┼─────────────────┐               │
│         ▼                 ▼                 ▼               │
│    ┌─────────┐       ┌─────────┐       ┌─────────┐         │
│    │ Brain 1 │       │ Brain 2 │       │ Brain 3 │         │
│    │ (active)│       │ (active)│       │ (active)│         │
│    └────┬────┘       └────┬────┘       └────┬────┘         │
│         └─────────────────┼─────────────────┘               │
│                           ▼                                  │
│                  ┌───────────────┐                          │
│                  │ Redis Cluster │                          │
│                  └───────────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

**Pros:** Maximum throughput, no failover delay
**Cons:** State synchronization complexity

### Active-Passive

```
┌─────────────────────────────────────────────────────────────┐
│         Primary                    Standby                  │
│    ┌─────────────┐            ┌─────────────┐              │
│    │   Brain 1   │───sync────▶│   Brain 2   │              │
│    │  (active)   │            │  (standby)  │              │
│    └─────────────┘            └─────────────┘              │
│          │                          │                       │
│          ▼                          ▼                       │
│    ┌─────────────┐            ┌─────────────┐              │
│    │  Primary DB │───repl────▶│ Replica DB  │              │
│    └─────────────┘            └─────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

**Pros:** Simpler state management
**Cons:** Failover delay (seconds)

---

## Failover Configuration

### Kubernetes

```yaml
# pod-disruption-budget.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: sentinel-brain-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: sentinel-brain
```

### Health Checks

```python
# app.py
from fastapi import FastAPI
from sentinel.health import HealthChecker

app = FastAPI()
health = HealthChecker()

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "redis": await health.check_redis(),
        "postgres": await health.check_postgres(),
        "engines": health.check_engines()
    }

@app.get("/ready")
async def readiness_check():
    # Only ready when all engines loaded
    if not health.engines_loaded():
        return {"status": "not ready"}, 503
    return {"status": "ready"}
```

---

## Redis Cluster

```yaml
# redis-cluster.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis-cluster
spec:
  serviceName: redis-cluster
  replicas: 6  # 3 masters + 3 replicas
  template:
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        command: ["redis-server", "--cluster-enabled", "yes"]
```

---

## Disaster Recovery

| RPO | RTO | Strategy |
|-----|-----|----------|
| 0 | <1min | Sync replication + Active-Active |
| <5min | <5min | Async replication + Hot standby |
| <1h | <1h | Backup restore |

```bash
# Backup
pg_dump sentinel > backup_$(date +%Y%m%d).sql

# Restore
psql sentinel < backup_20260118.sql
```

---

## Следующий урок

→ [2.1: SIEM Integration](./05-siem-integration.md)
