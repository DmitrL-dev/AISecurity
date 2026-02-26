# 🐳 Урок 1.2: Docker Deployment

> **Время: 25 минут** | Mid-Level Module 1

---

## Quick Start

```bash
# One-liner deployment
docker run -d -p 8080:8080 sentinel/brain:latest
```

---

## Production docker-compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  sentinel-brain:
    image: sentinel/brain:v4.1
    ports:
      - "8080:8080"
    environment:
      - SENTINEL_MODE=production
      - SENTINEL_ENGINES=all
      - REDIS_URL=redis://redis:6379
      - POSTGRES_URL=postgres://postgres:5432/sentinel
      - LOG_LEVEL=info
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
    depends_on:
      - redis
      - postgres

  sentinel-shield:
    image: sentinel/shield:v4.1
    ports:
      - "443:443"
    environment:
      - SHIELD_MODE=production
      - BRAIN_URL=http://sentinel-brain:8080
      - TLS_ENABLED=true
    volumes:
      - ./certs:/etc/ssl/sentinel:ro
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    deploy:
      resources:
        limits:
          memory: 1G

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=sentinel
      - POSTGRES_USER=sentinel
      - POSTGRES_PASSWORD_FILE=/run/secrets/db_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    secrets:
      - db_password

volumes:
  redis_data:
  postgres_data:

secrets:
  db_password:
    file: ./secrets/db_password.txt
```

---

## Dockerfile Best Practices

```dockerfile
# Dockerfile.brain
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim

# Security: non-root user
RUN useradd -m -u 1000 sentinel
USER sentinel

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --chown=sentinel:sentinel . .

# Health check
HEALTHCHECK --interval=30s --timeout=5s \
  CMD python -c "import requests; requests.get('http://localhost:8080/health')"

EXPOSE 8080
CMD ["python", "-m", "uvicorn", "sentinel.api:app", "--host", "0.0.0.0", "--port", "8080"]
```

---

## Environment Configuration

```bash
# .env.production

# Core
SENTINEL_MODE=production
SENTINEL_VERSION=v4.1

# Engines
SENTINEL_ENGINES=all
SENTINEL_TIER1_ONLY=false

# Performance
SENTINEL_WORKERS=4
SENTINEL_TIMEOUT_MS=200
SENTINEL_CACHE_TTL=300

# Security
SENTINEL_API_KEY_REQUIRED=true
SENTINEL_RATE_LIMIT=1000

# Logging
LOG_LEVEL=info
LOG_FORMAT=json
LOG_OUTPUT=stdout

# Connections
REDIS_URL=redis://redis:6379/0
POSTGRES_URL=postgres://sentinel:password@postgres:5432/sentinel

# Metrics
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
```

---

## Commands

```bash
# Start
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose logs -f sentinel-brain

# Scale
docker-compose up -d --scale sentinel-brain=3

# Health check
curl http://localhost:8080/health

# Metrics
curl http://localhost:9090/metrics
```

---

## Monitoring

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'sentinel-brain'
    static_configs:
      - targets: ['sentinel-brain:9090']
    scrape_interval: 15s

  - job_name: 'sentinel-shield'
    static_configs:
      - targets: ['sentinel-shield:9090']
```

---

## Следующий урок

→ [1.3: Kubernetes](./03-kubernetes.md)
