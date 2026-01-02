# SENTINEL Shield Configuration Guide

## Overview

This guide covers all configuration options for SENTINEL Shield.

---

## Configuration File

Shield configuration is stored in JSON format:

```bash
# Default locations
/etc/shield/config.json     # Linux
C:\ProgramData\Shield\config.json  # Windows
~/.shield/config.json       # User-specific
```

---

## Minimal Configuration

```json
{
  "version": "1.2.0",
  "zones": [{ "name": "external", "trust_level": 1 }],
  "guards": ["llm"]
}
```

---

## Full Configuration Reference

```json
{
  // === Core ===
  "version": "1.2.0",
  "name": "shield-prod-01",
  "log_level": "info",
  "log_file": "/var/log/shield/shield.log",

  // === Zones ===
  "zones": [
    {
      "name": "external",
      "trust_level": 1,
      "rate_limit": {
        "requests_per_second": 100,
        "burst": 200
      }
    },
    {
      "name": "internal",
      "trust_level": 10,
      "bypass_rules": false
    },
    {
      "name": "dmz",
      "trust_level": 5
    }
  ],

  // === Rules ===
  "rules": [
    {
      "id": 1,
      "name": "block_injection",
      "zone": "external",
      "direction": "inbound",
      "pattern": "ignore.*previous|disregard.*all",
      "pattern_type": "regex",
      "case_insensitive": true,
      "action": "block",
      "severity": 9,
      "enabled": true
    },
    {
      "id": 2,
      "name": "block_jailbreak",
      "pattern": "DAN|do anything now|developer mode",
      "action": "block",
      "severity": 10
    }
  ],

  // === Guards ===
  "guards": ["llm", "rag", "agent", "tool", "mcp", "api"],

  "guard_config": {
    "llm": {
      "max_tokens": 4096,
      "check_injection": true,
      "check_jailbreak": true
    },
    "rag": {
      "check_poisoning": true,
      "validate_sources": true
    },
    "agent": {
      "max_steps": 10,
      "allowed_tools": ["search", "calculator"]
    }
  },

  // === Analysis ===
  "semantic": {
    "enabled": true,
    "intent_threshold": 0.7,
    "detect_roleplay": true,
    "detect_social_engineering": true
  },

  "encoding": {
    "detect_obfuscation": true,
    "max_decode_layers": 3
  },

  "signatures": {
    "load_builtin": true,
    "custom_file": "/etc/shield/signatures.txt"
  },

  "anomaly": {
    "enabled": true,
    "z_threshold": 3.0,
    "min_samples": 100
  },

  // === Output Filtering ===
  "output_filter": {
    "enabled": true,
    "redact_pii": true,
    "redact_secrets": true,
    "redact_emails": true,
    "custom_patterns": [
      { "name": "internal_id", "pattern": "INT-[0-9]+", "action": "mask" }
    ]
  },

  // === Context Management ===
  "context": {
    "max_tokens": 8192,
    "eviction_policy": "oldest",
    "history_size": 1000
  },

  "safety_prompt": {
    "enabled": true,
    "inject_system": true,
    "inject_prefix": true,
    "reminder_every_n_turns": 5
  },

  // === Rate Limiting ===
  "rate_limit": {
    "global": {
      "requests_per_second": 1000,
      "burst": 2000
    },
    "per_session": {
      "requests_per_minute": 60,
      "burst": 100
    }
  },

  // === Blocklist ===
  "blocklist": {
    "ips": ["10.0.0.1", "192.168.1.0/24"],
    "sessions": [],
    "patterns": ["malicious-pattern"]
  },

  // === Canary ===
  "canary": {
    "enabled": true,
    "tokens": ["CANARY_TOKEN_1", "SECRET_MARKER_XYZ"]
  },

  // === High Availability ===
  "ha": {
    "enabled": false,
    "mode": "active-standby",
    "node_id": "node-01",
    "peers": [
      { "address": "10.0.1.2", "port": 5001 },
      { "address": "10.0.1.3", "port": 5001 }
    ],
    "heartbeat_interval_ms": 1000,
    "failover_timeout_ms": 5000
  },

  // === Metrics ===
  "metrics": {
    "prometheus": {
      "enabled": true,
      "port": 9090,
      "path": "/metrics"
    },
    "statsd": {
      "enabled": false,
      "host": "localhost",
      "port": 8125
    }
  },

  // === API ===
  "api": {
    "enabled": true,
    "port": 8080,
    "bind": "0.0.0.0",
    "auth": {
      "type": "api_key",
      "keys": ["YOUR_API_KEY"]
    }
  },

  // === CLI ===
  "cli": {
    "port": 2222,
    "bind": "127.0.0.1"
  },

  // === Audit ===
  "audit": {
    "enabled": true,
    "file": "/var/log/shield/audit.log",
    "syslog": {
      "enabled": false,
      "host": "localhost",
      "port": 514
    }
  },

  // === Webhooks ===
  "webhooks": {
    "on_block": {
      "url": "https://example.com/webhook/blocked",
      "method": "POST"
    },
    "on_alert": {
      "url": "https://example.com/webhook/alert",
      "method": "POST"
    }
  },

  // === Performance ===
  "performance": {
    "thread_pool_size": 4,
    "event_queue_size": 10000,
    "memory_pool_blocks": 1024
  },

  // === TLS ===
  "tls": {
    "enabled": false,
    "cert_file": "/etc/shield/cert.pem",
    "key_file": "/etc/shield/key.pem"
  }
}
```

---

## Environment Variables

Override config with environment variables:

| Variable              | Description               | Default                   |
| --------------------- | ------------------------- | ------------------------- |
| `SHIELD_CONFIG`       | Config file path          | `/etc/shield/config.json` |
| `SHIELD_LOG_LEVEL`    | Log level                 | `info`                    |
| `SHIELD_API_PORT`     | API port                  | `8080`                    |
| `SHIELD_METRICS_PORT` | Metrics port              | `9090`                    |
| `SHIELD_DATA_DIR`     | Data directory            | `/var/lib/shield`         |
| `HA_PEERS`            | Comma-separated peer list | -                         |

---

## Configuration Reload

```bash
# Via CLI
Shield> config reload

# Via API
curl -X POST http://localhost:8080/api/v1/config/reload

# Via signal (Linux)
kill -HUP $(pidof shield)
```

---

## Validation

```bash
# Validate config file
shield --validate-config /etc/shield/config.json

# Output
Config validation: OK
  - Zones: 3 defined
  - Rules: 12 defined
  - Guards: 6 enabled
```

---

## See Also

- [API Reference](API.md)
- [Architecture](ARCHITECTURE.md)
- [Deployment](DEPLOYMENT.md)
