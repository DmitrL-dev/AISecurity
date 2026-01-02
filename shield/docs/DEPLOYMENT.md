# SENTINEL Shield Deployment Guide

## Deployment Options

### Standalone Binary

Simplest deployment - single executable:

```bash
# Build
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build

# Deploy
cp build/sentinel-shield /usr/local/bin/
cp data/blocklist.txt /etc/sentinel/
```

### Docker

Production-ready container:

```bash
# Build image
docker build -t sentinel-shield:1.0.0 .

# Run
docker run -d \
  --name shield \
  -p 8080:8080 \
  -p 9090:9090 \
  -v /etc/sentinel:/etc/sentinel:ro \
  -v /var/log/sentinel:/var/log/sentinel \
  sentinel-shield:1.0.0
```

### Docker Compose

With monitoring stack:

```yaml
version: "3.8"

services:
  shield:
    image: sentinel-shield:1.0.0
    ports:
      - "8080:8080"
      - "9090:9090"
    volumes:
      - ./config:/etc/sentinel:ro
      - shield-logs:/var/log/sentinel
    environment:
      - SHIELD_LOG_LEVEL=info
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9091:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

volumes:
  shield-logs:
  prometheus-data:
  grafana-data:
```

### Kubernetes

Deployment manifest:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sentinel-shield
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
          image: sentinel-shield:1.0.0
          ports:
            - containerPort: 8080
              name: api
            - containerPort: 9090
              name: metrics
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 1000m
              memory: 512Mi
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 5
          volumeMounts:
            - name: config
              mountPath: /etc/sentinel
              readOnly: true
      volumes:
        - name: config
          configMap:
            name: shield-config
---
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
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: shield-config
data:
  shield.conf: |
    hostname kubernetes
    zone default
      type llm
    !
    shield-rule 10 block input llm pattern "ignore.*instructions"
    shield-rule 1000 allow input any
    !
    api enable
    api port 8080
    end
```

### High Availability

Active/Standby with SHSP:

```yaml
# Primary
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: shield-ha
spec:
  serviceName: shield-ha
  replicas: 2
  selector:
    matchLabels:
      app: shield-ha
  template:
    metadata:
      labels:
        app: shield-ha
    spec:
      containers:
        - name: shield
          image: sentinel-shield:1.0.0
          env:
            - name: POD_NAME
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
            - name: HA_PEERS
              value: "shield-ha-0.shield-ha:5400,shield-ha-1.shield-ha:5400"
          ports:
            - containerPort: 8080
            - containerPort: 5400
              name: shsp
```

## Environment Variables

| Variable              | Default                     | Description      |
| --------------------- | --------------------------- | ---------------- |
| `SHIELD_CONFIG`       | `/etc/sentinel/shield.conf` | Config file path |
| `SHIELD_LOG_LEVEL`    | `info`                      | Log level        |
| `SHIELD_API_PORT`     | `8080`                      | API port         |
| `SHIELD_METRICS_PORT` | `9090`                      | Metrics port     |
| `SHIELD_DATA_DIR`     | `/var/lib/sentinel`         | Data directory   |

## Monitoring

### Prometheus Config

```yaml
scrape_configs:
  - job_name: "shield"
    static_configs:
      - targets: ["shield:9090"]
    scrape_interval: 15s
```

### Key Metrics

```
# Request rate
rate(shield_requests_total[5m])

# Block rate
rate(shield_requests_blocked[5m]) / rate(shield_requests_total[5m])

# Latency p99
histogram_quantile(0.99, rate(shield_request_duration_seconds_bucket[5m]))

# Error rate
rate(shield_errors_total[5m])
```

### Grafana Dashboard

Import dashboard from `grafana/shield-dashboard.json`.

## Logging

### Syslog

```bash
docker run -d \
  -e SHIELD_SYSLOG_HOST=syslog.example.com \
  -e SHIELD_SYSLOG_PORT=514 \
  sentinel-shield:1.0.0
```

### JSON Logging

```bash
SHIELD_LOG_FORMAT=json ./sentinel-shield
```

### Audit Logs

```
/var/log/sentinel/audit.log
```

## Security Hardening

### Non-root User

```dockerfile
FROM sentinel-shield:1.0.0
USER nobody
```

### Read-only Filesystem

```bash
docker run --read-only \
  --tmpfs /tmp \
  sentinel-shield:1.0.0
```

### Network Policy (Kubernetes)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: shield-policy
spec:
  podSelector:
    matchLabels:
      app: shield
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              role: api-gateway
      ports:
        - port: 8080
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: prometheus
      ports:
        - port: 9090
```

## Backup & Recovery

### Config Backup

```bash
#!/bin/bash
tar -czf shield-config-$(date +%Y%m%d).tar.gz /etc/sentinel/
```

### State Export

```bash
curl http://localhost:8080/admin/export > shield-state.json
```

## Troubleshooting

### Common Issues

1. **Connection refused**

   - Check if container is running
   - Verify port mappings

2. **High memory usage**

   - Reduce session timeout
   - Lower quarantine limit

3. **High latency**
   - Check rule complexity
   - Increase thread pool

### Debug Mode

```bash
SHIELD_LOG_LEVEL=debug ./sentinel-shield
```

### Health Check

```bash
curl http://localhost:8080/health | jq
```
