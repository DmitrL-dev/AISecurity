# Configuration Guide

## Configuration File

Create `config.yaml` in your project root:

```yaml
sentinel:
  # Enabled engines
  engines:
    - injection
    - pii
    - rag_guard
    - tda_enhanced
    - sheaf_coherence
    - visual_content
    - cross_modal
    - probing_detection

  # Detection thresholds
  thresholds:
    block: 0.7 # Block if risk >= 0.7
    warn: 0.5 # Warn if risk >= 0.5
    log: 0.3 # Log if risk >= 0.3

  # Logging
  logging:
    level: INFO
    format: json

  # Performance
  performance:
    timeout_ms: 500
    max_concurrent: 10
```

## Environment Variables

```bash
# API
SENTINEL_HOST=0.0.0.0
SENTINEL_PORT=8000

# Engines
SENTINEL_ENGINES=injection,pii,rag_guard

# Thresholds
SENTINEL_BLOCK_THRESHOLD=0.7
SENTINEL_WARN_THRESHOLD=0.5

# Logging
LOG_LEVEL=INFO
```

## Per-Engine Configuration

### Injection Detector

```yaml
engines:
  injection:
    enabled: true
    patterns:
      - "ignore previous"
      - "disregard instructions"
    severity_weight: 1.0
```

### PII Detector

```yaml
engines:
  pii:
    enabled: true
    entities:
      - PERSON
      - EMAIL_ADDRESS
      - PHONE_NUMBER
      - CREDIT_CARD
    action: mask # mask, block, or log
```

### TDA Enhanced

```yaml
engines:
  tda_enhanced:
    enabled: true
    max_dimension: 2
    threshold: 0.5
```

## Loading Configuration

```python
from sentinel.config import load_config

config = load_config("config.yaml")
guard = SentinelGuard(config)
```

---

## Next Steps

- [Quick Start](../getting-started/quickstart.md)
- [API Reference](../reference/api.md)
