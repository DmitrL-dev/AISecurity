# SENTINEL Academy — Module 10

## Enterprise Deployment

_SSP Level | Время: 5 часов_

---

## Введение

Ты готов к production.

Этот модуль — всё что нужно для enterprise deployment.

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

### Multi-Region

```
           ┌───────────────────┐
           │   GLOBAL LB       │
           └─────────┬─────────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                │
┌───▼───┐       ┌───▼───┐        ┌───▼───┐
│ US-EAST│       │ EU-WEST│        │ APAC  │
│Cluster │       │Cluster │        │Cluster│
└────────┘       └────────┘        └────────┘
```

**Use case:** Global apps, low latency requirements.

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
COPY --from=builder /build/build/libsentinel-shield.so /usr/local/lib/

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
      - shield-logs:/var/log/shield
    environment:
      - SHIELD_NODE_ID=node-1
      - SHIELD_HA_ROLE=primary
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:8080/health"]
      interval: 5s
      timeout: 3s
      retries: 3
    restart: unless-stopped

  shield-standby:
    image: sentinel/shield:1.2.0
    hostname: shield-standby
    ports:
      - "8081:8080"
      - "9091:9090"
    volumes:
      - ./config/standby.json:/etc/shield/config.json:ro
      - shield-logs:/var/log/shield
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
    depends_on:
      - shield-primary
      - shield-standby
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9092:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
    restart: unless-stopped

volumes:
  shield-logs:
  grafana-data:
```

---

## 10.3 Kubernetes Deployment

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: shield
  labels:
    app: shield
spec:
  replicas: 3
  selector:
    matchLabels:
      app: shield
  template:
    metadata:
      labels:
        app: shield
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
    spec:
      containers:
        - name: shield
          image: sentinel/shield:1.2.0
          ports:
            - containerPort: 8080
              name: api
            - containerPort: 9090
              name: metrics
            - containerPort: 5001
              name: cluster
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
            initialDelaySeconds: 10
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 5
          volumeMounts:
            - name: config
              mountPath: /etc/shield
              readOnly: true
      volumes:
        - name: config
          configMap:
            name: shield-config
```

### Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: shield
spec:
  selector:
    app: shield
  ports:
    - name: api
      port: 8080
      targetPort: 8080
    - name: metrics
      port: 9090
      targetPort: 9090
  type: ClusterIP

---
apiVersion: v1
kind: Service
metadata:
  name: shield-headless
spec:
  selector:
    app: shield
  clusterIP: None
  ports:
    - name: cluster
      port: 5001
```

### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: shield-config
data:
  config.json: |
    {
      "version": "1.2.0",
      "name": "shield-k8s",
      "zones": [
        {"name": "external", "trust_level": 1}
      ],
      "rules": [
        {"name": "block_injection", "pattern": "ignore.*previous", "action": "block"}
      ],
      "api": {"enabled": true, "port": 8080},
      "metrics": {"prometheus": {"enabled": true, "port": 9090}}
    }
```

### Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: shield-ingress
  annotations:
    nginx.ingress.kubernetes.io/proxy-read-timeout: "5"
    nginx.ingress.kubernetes.io/proxy-connect-timeout: "2"
spec:
  rules:
    - host: shield.example.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: shield
                port:
                  number: 8080
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
    - type: Pods
      pods:
        metric:
          name: shield_request_rate
        target:
          type: AverageValue
          averageValue: "100"
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
      "type": "bearer",
      "token_validation": "jwt",
      "jwt_secret_file": "/etc/shield/jwt-secret"
    },
    "admin_auth": {
      "enabled": true,
      "users": [{ "username": "admin", "password_hash": "$2a$..." }]
    },
    "rate_limiting": {
      "enabled": true,
      "global_rps": 10000,
      "per_ip_rps": 100
    }
  }
}
```

### Performance Tuning

```json
{
  "performance": {
    "threads": 0,
    "max_connections": 10000,
    "connection_timeout_ms": 5000,
    "request_timeout_ms": 1000,
    "memory_pool_mb": 256,
    "pattern_cache_size": 10000
  }
}
```

### Logging for Production

```json
{
  "logging": {
    "level": "info",
    "format": "json",
    "sampling": {
      "enabled": true,
      "rate": 0.01
    },
    "fields_to_redact": ["input", "output"],
    "include_stack_trace": false
  }
}
```

---

## 10.5 Capacity Planning

### Sizing Guidelines

| Requests/sec | CPU Cores | Memory | Instances |
| ------------ | --------- | ------ | --------- |
| < 100        | 1         | 256MB  | 1         |
| 100 - 1K     | 2         | 512MB  | 2 (HA)    |
| 1K - 10K     | 4         | 1GB    | 3+        |
| > 10K        | 8+        | 2GB+   | 5+        |

### Key Metrics for Scaling

```yaml
# Scale up when:
cpu_utilization > 70%
memory_utilization > 80%
request_latency_p99 > 10ms
request_queue_size > 100

# Scale down when:
cpu_utilization < 30%
request_latency_p99 < 1ms
```

---

## 10.6 Backup & Recovery

### Configuration Backup

```bash
# Backup config
shield-cli config export > config_backup_$(date +%Y%m%d).json

# Restore config
shield-cli config import < config_backup.json
```

### State Backup

```bash
# Backup state (sessions, blocklists)
shield-cli state export > state_backup_$(date +%Y%m%d).json

# Restore state
shield-cli state import < state_backup.json
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
5. Sync state to new node
6. Resume normal operation
```

---

## 10.7 Upgrade Strategy

### Rolling Upgrade

```bash
# For Kubernetes
kubectl set image deployment/shield shield=sentinel/shield:1.2.1

# Rolling update with max 1 unavailable
kubectl rollout status deployment/shield
```

### Blue-Green Deployment

```
1. Deploy v1.2.1 (green) alongside v1.2.0 (blue)
2. Test green deployment
3. Switch traffic from blue to green
4. Verify
5. Tear down blue
```

### Canary Deployment

```yaml
# 10% traffic to canary
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    nginx.ingress.kubernetes.io/canary: "true"
    nginx.ingress.kubernetes.io/canary-weight: "10"
```

---

## 10.8 Operational Runbook

### Daily Checks

- [ ] Health status: All nodes healthy
- [ ] Block rate: Within expected range
- [ ] Latency P99: < 10ms
- [ ] Error rate: < 0.1%
- [ ] Disk usage: < 80%

### Weekly Checks

- [ ] Review blocked requests
- [ ] Update threat patterns
- [ ] Check log rotation
- [ ] Verify backups
- [ ] Review alerts

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

## Практика

### Задание 1

Разверни Shield в Docker Compose:

- Primary + Standby
- Nginx load balancer
- Prometheus + Grafana

### Задание 2

Создай Kubernetes deployment:

- 3 replicas
- HPA
- Ingress

### Задание 3

Напиши runbook:

- Daily checks
- Incident response
- Rollback procedure

---

## Итоги Module 10

- Docker и Kubernetes deployment
- Production hardening
- Capacity planning
- Backup & recovery
- Upgrade strategies
- Operational runbooks

---

## 🎉 SSP Complete!

Ты прошёл все 10 модулей (SSA + SSP):

**SSA (Modules 0-5):** Фундамент
**SSP (Modules 6-10):** Профессиональный уровень

**Готов к сертификации SSP-200!**

---

## Следующий шаг

**SSE (Expert):** Modules 11-15

- Internals
- Custom Guard Development
- Plugin System
- Performance Engineering
- Capstone Project

---

_"Production is not a destination, it's a responsibility."_
