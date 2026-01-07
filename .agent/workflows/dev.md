---
description: Quick dev workflow with auto-run commands
---

# Sentinel Development Workflow

// turbo-all

## Build & Test

1. Rebuild and start all containers:

```bash
docker-compose up -d --build
```

2. Check logs:

```bash
docker-compose logs --tail 20
```

3. Test health endpoint:

```bash
curl http://localhost:8080/health
```

4. Test safe prompt:

```bash
curl -X POST http://localhost:8080/v1/chat/completions -H "Content-Type: application/json" -d '{"messages": [{"role": "user", "content": "Hello"}]}'
```

5. Test login (when AUTH_ENABLED=true):

```bash
curl -X POST http://localhost:8080/auth/login -H "Content-Type: application/json" -d '{"user_id": "admin", "password": "sentinel"}'
```

## Quick Fixes

6. View Gateway logs:

```bash
docker-compose logs gateway --tail 10
```

7. View Brain logs:

```bash
docker-compose logs brain --tail 10
```

8. Restart services:

```bash
docker-compose restart
```
