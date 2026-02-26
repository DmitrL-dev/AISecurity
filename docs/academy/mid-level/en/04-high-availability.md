# 🔄 Lesson 1.4: High Availability

> **Time: 25 minutes** | Mid-Level Module 1

---

## HA Patterns

| Pattern | Recovery Time | Complexity |
|---------|---------------|------------|
| **Active-Passive** | Seconds | Low |
| **Active-Active** | Zero | Medium |
| **Multi-Region** | Zero | High |

---

## Active-Active

```yaml
# Kubernetes: Multiple replicas
apiVersion: apps/v1
kind: Deployment
spec:
  replicas: 3  # All active
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 1
```

---

## Load Balancing

```yaml
apiVersion: v1
kind: Service
metadata:
  name: sentinel-brain
spec:
  type: LoadBalancer
  sessionAffinity: None  # Stateless
  ports:
  - port: 80
    targetPort: 8080
```

---

## Redis Cluster (Caching)

```yaml
sentinel:
  redis:
    cluster:
      enabled: true
      nodes:
        - redis-0:6379
        - redis-1:6379
        - redis-2:6379
```

---

## Health Checks

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/ready")
async def ready():
    # Check dependencies
    redis_ok = await check_redis()
    brain_ok = await check_brain()
    
    if redis_ok and brain_ok:
        return {"status": "ready"}
    return Response(status_code=503)
```

---

## Disaster Recovery

| RPO | RTO | Strategy |
|-----|-----|----------|
| 0 | 0 | Active-Active multi-region |
| <1h | <5m | Hot standby |
| <24h | <1h | Cold standby + backups |

---

## Next Lesson

→ [2.1: SIEM Integration](./05-siem-integration.md)
