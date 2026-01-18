# 🐳 Lesson 1.2: Docker Deployment

> **Time: 45 minutes** | Mid-Level Module 1

---

## Quick Start

```bash
curl -sSL https://raw.githubusercontent.com/DmitrL-dev/AISecurity/main/install.sh | bash
```

---

## docker-compose.yml

```yaml
version: '3.8'

services:
  brain:
    image: sentinel/brain:v4.1
    ports:
      - "8080:8080"
    environment:
      - SENTINEL_LOG_LEVEL=info
      - SENTINEL_ENGINES=all
    volumes:
      - ./config:/app/config
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

---

## Dockerfile (Custom)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install SENTINEL
RUN pip install --no-cache-dir sentinel-llm-security[full]

# Copy config
COPY config/ /app/config/

# Non-root user
RUN useradd -m sentinel && chown -R sentinel:sentinel /app
USER sentinel

EXPOSE 8080

CMD ["sentinel", "serve", "--host", "0.0.0.0", "--port", "8080"]
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SENTINEL_LOG_LEVEL` | `info` | Logging level |
| `SENTINEL_ENGINES` | `all` | Enabled engines |
| `SENTINEL_THRESHOLD` | `0.7` | Detection threshold |
| `SENTINEL_REDIS_URL` | `None` | Redis for caching |
| `SENTINEL_API_KEY` | `None` | API authentication |

---

## Production Checklist

- [ ] Non-root user in container
- [ ] Health checks configured
- [ ] Resource limits set
- [ ] Secrets via environment/vault
- [ ] Logging to stdout
- [ ] Metrics endpoint exposed

---

## Next Lesson

→ [1.3: Kubernetes](./03-kubernetes.md)
