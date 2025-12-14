# 🚀 SENTINEL — Production Deployment Guide

> **Reading time:** 30 minutes  
> **Level:** Intermediate — Advanced  
> **Result:** Production-ready SENTINEL deployment

---

## Contents

1. [Architecture Overview](#architecture-overview)
2. [Infrastructure Requirements](#infrastructure-requirements)
3. [Security](#security)
4. [Docker Compose Production](#docker-compose-production)
5. [Kubernetes Production](#kubernetes-production)
6. [Monitoring](#monitoring)
7. [Logging](#logging)
8. [Scaling](#scaling)
9. [Backup and Recovery](#backup-and-recovery)
10. [Production Checklist](#production-checklist)

---

## Architecture Overview

### Production Architecture

```
                            ┌─────────────────────────────────────────────────┐
                            │                   INTERNET                       │
                            └─────────────────────────────────────────────────┘
                                                    │
                                                    ▼
                            ┌─────────────────────────────────────────────────┐
                            │              LOAD BALANCER                       │
                            │         (nginx / AWS ALB / Cloudflare)          │
                            │              TLS Termination                     │
                            └─────────────────────────────────────────────────┘
                                                    │
                        ┌───────────────────────────┼───────────────────────────┐
                        │                           │                           │
                        ▼                           ▼                           ▼
                ┌───────────────┐           ┌───────────────┐           ┌───────────────┐
                │   GATEWAY 1   │           │   GATEWAY 2   │           │   GATEWAY 3   │
                │    (Go)       │           │    (Go)       │           │    (Go)       │
                └───────────────┘           └───────────────┘           └───────────────┘
                        │                           │                           │
                        └───────────────────────────┼───────────────────────────┘
                                                    │
                                            ┌───────┴───────┐
                                            │  gRPC + mTLS  │
                                            └───────┬───────┘
                        ┌───────────────────────────┼───────────────────────────┐
                        │                           │                           │
                        ▼                           ▼                           ▼
                ┌───────────────┐           ┌───────────────┐           ┌───────────────┐
                │    BRAIN 1    │           │    BRAIN 2    │           │    BRAIN 3    │
                │   (Python)    │           │   (Python)    │           │   (Python)    │
                │  89 engines   │           │  89 engines   │           │  89 engines   │
                └───────────────┘           └───────────────┘           └───────────────┘
```

### Components

| Component         | Role                             | Scaling            |
| ----------------- | -------------------------------- | ------------------ |
| **Load Balancer** | TLS termination, routing         | 1 (HA pair)        |
| **Gateway**       | HTTP → gRPC, auth, rate limiting | 2-10 replicas      |
| **Brain**         | ML engines, analysis             | 3-20 replicas      |
| **Redis**         | Cache, sessions, rate limits     | Cluster (3+ nodes) |
| **Prometheus**    | Metrics                          | 1-2 replicas       |

---

## Infrastructure Requirements

### Minimum Production

| Resource          | Quantity | Specification                     |
| ----------------- | -------- | --------------------------------- |
| **Servers**       | 3        | 8 CPU, 32 GB RAM, 100 GB SSD      |
| **Load Balancer** | 1        | nginx or cloud                    |
| **Redis**         | 1        | 4 GB RAM                          |
| **Network**       | —        | Low latency (<10ms between nodes) |

### Recommended Production

| Resource          | Quantity | Specification                    |
| ----------------- | -------- | -------------------------------- |
| **Gateway nodes** | 3        | 4 CPU, 8 GB RAM                  |
| **Brain nodes**   | 5        | 8 CPU, 32 GB RAM, GPU (optional) |
| **Redis Cluster** | 3        | 8 GB RAM each                    |
| **ELK Cluster**   | 3        | 8 CPU, 32 GB RAM, 500 GB SSD     |

---

## Security

### 1. TLS Certificates

```bash
# Generate CA
openssl genrsa -out certs/ca.key 4096
openssl req -new -x509 -days 365 -key certs/ca.key \
    -out certs/ca.crt \
    -subj "/CN=SENTINEL-CA"

# Generate server certificate
openssl genrsa -out certs/server.key 2048
openssl req -new -key certs/server.key \
    -out certs/server.csr \
    -subj "/CN=sentinel.example.com"

# Sign certificate
openssl x509 -req -days 365 \
    -in certs/server.csr \
    -CA certs/ca.crt \
    -CAkey certs/ca.key \
    -CAcreateserial \
    -out certs/server.crt
```

### 2. mTLS Configuration

```env
MTLS_ENABLED=true
MTLS_CA_FILE=./certs/ca.crt
MTLS_CERT_FILE=./certs/server.crt
MTLS_KEY_FILE=./certs/server.key
```

### 3. Secret Keys

```bash
# Generate JWT secret (minimum 32 bytes)
openssl rand -hex 32

# Generate Redis password
openssl rand -base64 32
```

---

## Docker Compose Production

### Production YAML

```yaml
version: "3.8"

services:
  gateway:
    image: sentinel/gateway:${VERSION:-latest}
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: "2"
          memory: 4G
    environment:
      - GATEWAY_MODE=production
      - AUTH_ENABLED=true
      - AUTH_SECRET=${AUTH_SECRET}
      - TLS_ENABLED=true
    volumes:
      - ./certs:/certs:ro
    ports:
      - "8080:8080"

  brain:
    image: sentinel/brain:${VERSION:-latest}
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: "4"
          memory: 16G
    environment:
      - BRAIN_ANALYSIS_MODE=balanced
      - BRAIN_WORKERS=4

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes
    volumes:
      - redis-data:/data

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/certs:ro
    ports:
      - "443:443"
      - "80:80"

volumes:
  redis-data:
```

### Startup

```bash
# Create production .env
cat > .env <<EOF
VERSION=1.0.0
AUTH_SECRET=$(openssl rand -hex 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
EOF

# Start
docker compose -f docker-compose.yml -f production.yml up -d

# Verify
curl -k https://localhost/health
```

---

## Kubernetes Production

### Helm Values

```yaml
replicaCount:
  gateway: 3
  brain: 5

gateway:
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70

brain:
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 20

redis:
  architecture: replication
  replica:
    replicaCount: 3

ingress:
  enabled: true
  className: nginx
  tls:
    - secretName: sentinel-tls
      hosts:
        - sentinel.your-domain.com

podDisruptionBudget:
  gateway:
    minAvailable: 2
  brain:
    minAvailable: 2
```

---

## Monitoring

### Prometheus Metrics

```
sentinel_requests_total{status="success"} 12345
sentinel_requests_total{status="blocked"} 456
sentinel_analysis_duration_seconds_bucket{le="0.05"} 500
sentinel_engines_triggered{engine="injection"} 234
```

### Alerting Rules

```yaml
groups:
  - name: sentinel
    rules:
      - alert: SentinelHighErrorRate
        expr: rate(sentinel_requests_total{status="error"}[5m]) > 0.01
        for: 5m
        labels:
          severity: critical

      - alert: SentinelHighLatency
        expr: histogram_quantile(0.95, rate(sentinel_analysis_duration_seconds_bucket[5m])) > 0.5
        for: 5m
        labels:
          severity: warning
```

---

## Logging

### JSON Format

```json
{
  "timestamp": "2024-12-12T10:30:00.000Z",
  "level": "INFO",
  "service": "brain",
  "request_id": "req-abc123",
  "risk_score": 0.85,
  "verdict": "HIGH_RISK",
  "engines_triggered": ["injection", "behavioral"],
  "duration_ms": 45
}
```

---

## Scaling

### Horizontal Scaling

| Component | Type    | Metric       | Target    |
| --------- | ------- | ------------ | --------- |
| Gateway   | HPA     | CPU          | 70%       |
| Brain     | HPA     | CPU + Memory | 70% / 80% |
| Redis     | Cluster | —            | 3+ nodes  |

### Vertical Scaling Brain

```yaml
brain:
  resources:
    limits:
      nvidia.com/gpu: 1 # GPU for Qwen
      memory: 32Gi
```

---

## Backup and Recovery

### Redis Backup

```bash
# Create backup
redis-cli -a $REDIS_PASSWORD BGSAVE
docker cp redis:/data/dump.rdb ./backups/redis-$(date +%Y%m%d).rdb

# Restore
docker cp ./backups/redis-20241212.rdb redis:/data/dump.rdb
docker restart redis
```

---

## Production Checklist

### Security

- [ ] TLS enabled
- [ ] AUTH_ENABLED=true
- [ ] Strong JWT secret (32+ bytes)
- [ ] Redis password set
- [ ] Firewall configured
- [ ] mTLS between services

### Reliability

- [ ] 3+ Gateway replicas
- [ ] 3+ Brain replicas
- [ ] Redis persistence enabled
- [ ] Health checks configured
- [ ] Pod Disruption Budget

### Monitoring

- [ ] Prometheus configured
- [ ] Grafana dashboards
- [ ] Alerting rules
- [ ] Log aggregation (ELK)

### Performance

- [ ] Resources limits set
- [ ] Autoscaling enabled
- [ ] Caching enabled
- [ ] Rate limiting configured

---

**Deployment complete! 🎉**

Next step: [Integration Guide →](./integration-en.md)
