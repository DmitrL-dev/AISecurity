# Engine Config Persistence — Integration Guide

## Status: Implemented ✅

Config теперь сохраняется в Redis (`sentinel:engine:config:{name}`)

## API

```
GET  /v1/engines/{name}/config  → Loads from Redis, merges with defaults
PATCH /v1/engines/{name}/config → Saves to Redis, returns {persisted: true}
```

## Files

- `src/brain/config_storage.py` — Redis CRUD
- `src/brain/api/v1/engines.py` — API endpoints

## TODO: Production Hardening

### 1. Redis Security
```yaml
# docker-compose.yml
redis:
  command: redis-server --requirepass ${REDIS_PASSWORD}
  
# .env
REDIS_URL=redis://:password@redis:6379
```

### 2. AOF Persistence
```
# redis.conf
appendonly yes
appendfsync everysec
```

### 3. Apply Config to Engine Runtime
```python
# В engines/registry.py добавить:
def apply_persisted_config(engine_name: str):
    from src.brain.config_storage import load_config
    config = load_config(engine_name)
    if config and engine_name in self._registry:
        engine = self._registry[engine_name]
        engine.threshold = config.get("threshold", engine.threshold)
```

### 4. Load on Startup
```python
# В main.py при старте:
from src.brain.config_storage import load_all_configs
for name, config in load_all_configs().items():
    registry.apply_config(name, config)
```

### 5. Audit Log Integration
```python
# При save_config добавить:
from src.brain.audit import log_config_change
log_config_change(engine_name, old_config, new_config, user="admin")
```
