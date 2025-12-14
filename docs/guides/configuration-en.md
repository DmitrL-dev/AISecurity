# ⚙️ SENTINEL — Configuration Guide

> **Reading time:** 20 minutes  
> **Level:** Intermediate  
> **Result:** System fully configured to your requirements

---

## Contents

1. [Configuration Overview](#configuration-overview)
2. [Environment Variables](#environment-variables)
3. [Engine Settings](#engine-settings)
4. [Security Thresholds](#security-thresholds)
5. [Rate Limiting](#rate-limiting)
6. [Language Filters](#language-filters)
7. [LLM Integration](#llm-integration)
8. [Analysis Modes](#analysis-modes)
9. [Logging](#logging)
10. [Configuration Examples](#configuration-examples)

---

## Configuration Overview

SENTINEL is configured via:

1. **Environment variables** — primary method
2. **Configuration files** — for complex settings
3. **API** — dynamic changes

### Priority Order

```
API (runtime) > Environment Variables > Config Files > Defaults
```

---

## Environment Variables

### Gateway Settings

| Variable                   | Type   | Default       | Description                  |
| -------------------------- | ------ | ------------- | ---------------------------- |
| `GATEWAY_PORT`             | int    | `8080`        | HTTP port                    |
| `GATEWAY_HOST`             | string | `0.0.0.0`     | Bind host                    |
| `GATEWAY_MODE`             | string | `development` | `development` / `production` |
| `GATEWAY_BRAIN_TIMEOUT`    | int    | `30`          | gRPC timeout (sec)           |
| `GATEWAY_MAX_REQUEST_SIZE` | int    | `10485760`    | Max request size (bytes)     |

### Brain Settings

| Variable              | Type   | Default    | Description        |
| --------------------- | ------ | ---------- | ------------------ |
| `BRAIN_PORT`          | int    | `50051`    | gRPC port          |
| `BRAIN_HOST`          | string | `brain`    | Brain host         |
| `BRAIN_WORKERS`       | int    | `0`        | Workers (0 = auto) |
| `BRAIN_ANALYSIS_MODE` | string | `balanced` | Analysis mode      |
| `BRAIN_CACHE_ENABLED` | bool   | `true`     | Result caching     |
| `BRAIN_CACHE_TTL`     | int    | `300`      | Cache TTL (sec)    |

### Authentication

| Variable           | Type   | Default  | Description             |
| ------------------ | ------ | -------- | ----------------------- |
| `AUTH_ENABLED`     | bool   | `false`  | Enable auth             |
| `AUTH_SECRET`      | string | —        | **REQUIRED** JWT secret |
| `AUTH_TOKEN_TTL`   | int    | `3600`   | Token lifetime (sec)    |
| `AUTH_REFRESH_TTL` | int    | `604800` | Refresh token TTL       |

### Engines

| Variable           | Type   | Default | Description        |
| ------------------ | ------ | ------- | ------------------ |
| `DISABLED_ENGINES` | string | —       | Disable engines    |
| `ENABLED_ENGINES`  | string | —       | Only these engines |
| `BLOCK_THRESHOLD`  | float  | `0.7`   | Block threshold    |
| `WARN_THRESHOLD`   | float  | `0.5`   | Warning threshold  |

### Rate Limiting

| Variable              | Type | Default | Description         |
| --------------------- | ---- | ------- | ------------------- |
| `RATE_LIMIT_ENABLED`  | bool | `true`  | Enable              |
| `RATE_LIMIT_REQUESTS` | int  | `100`   | Requests per window |
| `RATE_LIMIT_WINDOW`   | int  | `60`    | Window (sec)        |
| `RATE_LIMIT_BY_IP`    | bool | `true`  | Limit by IP         |
| `RATE_LIMIT_BY_TOKEN` | bool | `true`  | Limit by token      |

---

## Engine Settings

### Disabling Engines

```env
# Disable specific engines
DISABLED_ENGINES=quantum_ml,homomorphic_engine,neural_cryptography

# Or enable only specific engines
ENABLED_ENGINES=injection,behavioral,pii,prompt_guard
```

### Engine Weights in Meta-Judge

```yaml
# config/engine_weights.yaml
engines:
  injection:
    weight: 1.5 # High priority
    enabled: true
  behavioral:
    weight: 1.2
    enabled: true
  quantum_ml:
    weight: 0.5 # Low priority
    enabled: false
```

---

## Security Thresholds

### Global Thresholds

```env
BLOCK_THRESHOLD=0.7   # Auto-block
WARN_THRESHOLD=0.5    # Warning (logging)
AUDIT_THRESHOLD=0.3   # Audit
```

### Risk Score Actions

| Risk Score | Action | Logging  | Response         |
| ---------- | ------ | -------- | ---------------- |
| 0.0 — 0.3  | Pass   | Minimal  | Normal           |
| 0.3 — 0.5  | Audit  | Detailed | + Warning header |
| 0.5 — 0.7  | Warn   | Full     | + Risk score     |
| 0.7 — 1.0  | Block  | + Alert  | Rejection        |

---

## Language Filters

### Modes

| Mode        | Description              |
| ----------- | ------------------------ |
| `DISABLED`  | All languages allowed    |
| `WHITELIST` | Only specified languages |
| `BLACKLIST` | All except specified     |

### Configuration

```env
LANGUAGE_MODE=WHITELIST
ALLOWED_LANGUAGES=en,ru,zh,de,fr
LANGUAGE_MIN_CONFIDENCE=0.8
```

---

## LLM Integration

### OpenAI

```env
LLM_PROVIDER=openai
LLM_API_KEY=sk-...
LLM_API_BASE=https://api.openai.com/v1
LLM_DEFAULT_MODEL=gpt-4
```

### Azure OpenAI

```env
LLM_PROVIDER=azure
LLM_API_KEY=...
LLM_API_BASE=https://your-resource.openai.azure.com/
LLM_API_VERSION=2024-02-15-preview
LLM_DEPLOYMENT_NAME=gpt-4
```

### Anthropic Claude

```env
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-...
LLM_DEFAULT_MODEL=claude-3-opus-20240229
```

### Google Gemini

```env
LLM_PROVIDER=google
LLM_API_KEY=...
LLM_DEFAULT_MODEL=gemini-pro
```

### Local Models (Ollama/vLLM)

```env
LLM_PROVIDER=openai  # Compatible API
LLM_API_KEY=not-needed
LLM_API_BASE=http://localhost:11434/v1
LLM_DEFAULT_MODEL=llama2
```

---

## Analysis Modes

### Fast Mode

- ~10ms latency
- 15 basic engines
- Use: High load, real-time

### Balanced Mode (Recommended)

- ~50ms latency
- 40 engines
- Use: Production default

### Thorough Mode

- ~200ms latency
- All 89+ engines
- Use: Critical systems

---

## Logging

### Levels

- `DEBUG` — Everything including input data
- `INFO` — Standard operations
- `WARNING` — Potential problems
- `ERROR` — Errors
- `CRITICAL` — Critical failures

### Configuration

```env
LOG_LEVEL=INFO
LOG_FORMAT=json  # or text
LOG_FILE=/var/log/sentinel/sentinel.log
LOG_MAX_SIZE=100  # MB
LOG_MAX_FILES=10
```

---

## Configuration Examples

### Development

```env
AUTH_ENABLED=false
BRAIN_ANALYSIS_MODE=fast
LOG_LEVEL=DEBUG
RATE_LIMIT_ENABLED=false
```

### Production

```env
AUTH_ENABLED=true
AUTH_SECRET=<generated-32-byte-hex>
BRAIN_ANALYSIS_MODE=balanced
LOG_LEVEL=INFO
RATE_LIMIT_ENABLED=true
BLOCK_THRESHOLD=0.7
```

### High Security

```env
BRAIN_ANALYSIS_MODE=thorough
BLOCK_THRESHOLD=0.5
LANGUAGE_MODE=WHITELIST
ALLOWED_LANGUAGES=en,ru
RATE_LIMIT_REQUESTS=50
```

### High Performance

```env
BRAIN_ANALYSIS_MODE=fast
BRAIN_WORKERS=16
HEAVY_ENGINES_ENABLED=false
RATE_LIMIT_REQUESTS=1000
```

---

**Configuration complete! 🎉**

Next step: [Integration Guide →](./integration-en.md)
