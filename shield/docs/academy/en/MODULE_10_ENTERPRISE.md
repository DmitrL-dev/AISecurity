# SENTINEL Academy — Module 10

## Enterprise Deployment

_SSP Level | Duration: 5 hours_

---

## Introduction

You're ready for production.

This module — everything needed for enterprise deployment.

---

## 10.1 Deployment Models

### Single Instance

```
┌─────────────────────────────────────┐
│              SERVER                 │
│  ┌──────────────────────────────┐   │
│  │       SENTINEL SHIELD        │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

**Use case:** Dev, testing, small workloads.

### HA Cluster

```
            ┌───────────────┐
            │ Load Balancer │
            └───────┬───────┘
                    │
         ┌──────────┴──────────┐
         │                     │
    ┌────▼────┐           ┌────▼────┐
    │ Node 1  │◄─────────►│ Node 2  │
    │(Primary)│   SHSP    │(Standby)│
    └─────────┘           └─────────┘
```

**Use case:** Production, critical workloads.

---

## 10.2 Docker Deployment

### Dockerfile

```dockerfile
FROM alpine:3.19 AS builder

RUN apk add --no-cache gcc musl-dev cmake make

WORKDIR /build
COPY . .

RUN mkdir build && cd build && \
    cmake -DCMAKE_BUILD_TYPE=Release .. && \
    make -j$(nproc)

FROM alpine:3.19

RUN apk add --no-cache libgcc

COPY --from=builder /build/build/shield /usr/local/bin/
COPY --from=builder /build/build/shield-cli /usr/local/bin/

EXPOSE 8080 9090 5001

HEALTHCHECK --interval=5s --timeout=3s \
    CMD wget -q --spider http://localhost:8080/health || exit 1

ENTRYPOINT ["shield"]
CMD ["-c", "/etc/shield/config.json"]
```

### docker-compose.yml

```yaml
version: "3.8"

services:
  shield-primary:
    image: sentinel/shield:1.2.0
    hostname: shield-primary
    ports:
      - "8080:8080"
      - "9090:9090"
    volumes:
      - ./config/primary.json:/etc/shield/config.json:ro
    environment:
      - SHIELD_NODE_ID=node-1
      - SHIELD_HA_ROLE=primary
    restart: unless-stopped

  shield-standby:
    image: sentinel/shield:1.2.0
    hostname: shield-standby
    ports:
      - "8081:8080"
    environment:
      - SHIELD_NODE_ID=node-2
      - SHIELD_HA_ROLE=standby
    depends_on:
      - shield-primary
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9092:9090"

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
```

---

## 10.3 Kubernetes Deployment

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: shield
spec:
  replicas: 3
  selector:
    matchLabels:
      app: shield
  template:
    metadata:
      labels:
        app: shield
    spec:
      containers:
        - name: shield
          image: sentinel/shield:1.2.0
          ports:
            - containerPort: 8080
            - containerPort: 9090
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8080
```

### HorizontalPodAutoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: shield-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: shield
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

---

## 10.4 Production Configuration

### Security Hardening

```json
{
  "security": {
    "tls": {
      "enabled": true,
      "cert_file": "/etc/shield/tls/server.crt",
      "key_file": "/etc/shield/tls/server.key",
      "min_version": "TLS1.2"
    },
    "api_auth": {
      "enabled": true,
      "type": "bearer"
    },
    "rate_limiting": {
      "enabled": true,
      "global_rps": 10000,
      "per_ip_rps": 100
    }
  }
}
```

---

## 10.5 Capacity Planning

### Sizing Guidelines

| Requests/sec | CPU Cores | Memory | Instances |
|--------------|-----------|--------|-----------|
| < 100 | 1 | 256MB | 1 |
| 100 - 1K | 2 | 512MB | 2 (HA) |
| 1K - 10K | 4 | 1GB | 3+ |
| > 10K | 8+ | 2GB+ | 5+ |

---

## 10.6 Backup & Recovery

### Configuration Backup

```bash
# Backup config
shield-cli config export > config_backup_$(date +%Y%m%d).json

# Restore config
shield-cli config import < config_backup.json
```

### Disaster Recovery

```
RTO (Recovery Time Objective): < 5 minutes
RPO (Recovery Point Objective): < 1 minute

Procedure:
1. Detect failure (monitoring)
2. Failover to standby (automatic via SHSP)
3. Verify service restored
4. Replace failed node
5. Resume normal operation
```

---

## 10.7 Operational Runbook

### Daily Checks

- [ ] Health status: All nodes healthy
- [ ] Block rate: Within expected range
- [ ] Latency P99: < 10ms
- [ ] Error rate: < 0.1%

### Incident Response

```
1. DETECT: Alert triggers
2. TRIAGE: Assess severity
3. MITIGATE: Quick fix (restart, failover)
4. INVESTIGATE: Root cause analysis
5. RESOLVE: Permanent fix
6. POSTMORTEM: Document learnings
```

---

## 🎉 SSP Complete!

You've completed all 10 modules (SSA + SSP):

**SSA (Modules 0-5):** Foundation
**SSP (Modules 6-10):** Professional level

**Ready for SSP-200 certification!**

---

## Next Step

**SSE (Expert):** Modules 11-15

- Internals
- Custom Guard Development
- Plugin System
- Performance Engineering
- Capstone Project

---

_"Production is not a destination, it's a responsibility."_
