# SENTINEL Academy — Module 6

## Guards: Deep Dive

_SSP Level | Duration: 6 hours_

---

## Introduction

In SSA you learned what Guards are.

Now — complete dive into each of the 6 Guards.

---

## 6.1 Guard Architecture

### Vtable Interface

All Guards implement a unified interface:

```c
typedef struct {
    const char *name;
    guard_type_t type;

    // Lifecycle
    shield_err_t (*init)(void *config, void **ctx);
    void (*destroy)(void *ctx);

    // Core
    shield_err_t (*evaluate)(void *ctx,
                              const guard_event_t *event,
                              guard_result_t *result);

    // Optional
    shield_err_t (*validate_config)(const char *json);
    void (*get_stats)(void *ctx, guard_stats_t *stats);
} guard_vtable_t;
```

### Event Structure

```c
typedef struct {
    const char *input;         // Input text
    size_t input_len;
    const char *zone;          // Source zone
    direction_t direction;     // INBOUND/OUTBOUND

    // Context
    const char *session_id;
    const char *user_id;
    uint64_t timestamp;

    // Metadata (JSON)
    const char *metadata;
} guard_event_t;
```

### Result Structure

```c
typedef struct {
    action_t action;           // ALLOW, BLOCK, LOG
    float threat_score;        // 0.0 - 1.0
    char reason[256];          // Human-readable reason
    char details[1024];        // JSON with details
    uint64_t processing_ns;    // Processing time
} guard_result_t;
```

---

## 6.2 LLM Guard

### Purpose

Protect language models (ChatGPT, Claude, Gemini, etc.)

### Threats

| Threat | Description |
|--------|-------------|
| Prompt Injection | Command injection |
| Jailbreak | Bypass restrictions |
| Prompt Extraction | System prompt theft |
| Role Manipulation | Changing AI role |

### Configuration

```json
{
  "guards": [
    {
      "type": "llm",
      "enabled": true,
      "config": {
        "injection_detection": {
          "enabled": true,
          "sensitivity": "high",
          "patterns": ["ignore_previous", "new_instructions"]
        },
        "jailbreak_detection": {
          "enabled": true,
          "categories": ["dan", "roleplay", "hypothetical"],
          "threshold": 0.8
        },
        "prompt_leak_prevention": {
          "enabled": true,
          "canary_tokens": ["CANARY-XYZ-123"],
          "system_prompt_patterns": true
        },
        "role_enforcement": {
          "enabled": true,
          "allowed_roles": ["assistant", "helper"],
          "blocked_roles": ["admin", "developer", "DAN"]
        }
      }
    }
  ]
}
```

### Detection Methods

**1. Pattern-based:**

```c
// Known injection patterns
"ignore.*previous"
"disregard.*instructions"
"you are now"
"new role:"
```

**2. Semantic:**

```c
// ML intent classifier
intent = classify_intent(input);
if (intent == INTENT_INSTRUCTION_OVERRIDE) {
    return ACTION_BLOCK;
}
```

**3. Canary Tokens:**

```c
// If canary appears in output — prompt leak
if (contains(output, "CANARY-XYZ-123")) {
    log_alert("System prompt leaked!");
    return ACTION_BLOCK;
}
```

---

## 6.3 RAG Guard

### Purpose

Protect Retrieval-Augmented Generation systems.

### Threats

| Threat | Description |
|--------|-------------|
| Document Poisoning | Malicious docs in knowledge base |
| Context Injection | Instructions in retrieved docs |
| Citation Abuse | Source manipulation |
| Data Exfiltration | Theft via context |

### Configuration

```json
{
  "guards": [
    {
      "type": "rag",
      "enabled": true,
      "config": {
        "document_sanitization": {
          "enabled": true,
          "remove_instructions": true,
          "max_instruction_density": 0.1
        },
        "source_verification": {
          "enabled": true,
          "allowed_sources": ["internal_kb", "approved_docs"],
          "require_metadata": true
        },
        "context_limits": {
          "max_context_length": 8192,
          "max_documents": 5,
          "max_doc_length": 2048
        }
      }
    }
  ]
}
```

---

## 6.4 Agent Guard

### Purpose

Protect autonomous AI agents.

### Threats

| Threat | Description |
|--------|-------------|
| Goal Hijacking | Changing agent's goal |
| Memory Poisoning | Poisoning memory |
| Action Abuse | Unauthorized actions |
| Loop Exploitation | Infinite loops |

### Configuration

```json
{
  "guards": [
    {
      "type": "agent",
      "enabled": true,
      "config": {
        "goal_protection": {
          "enabled": true,
          "lock_original_goal": true,
          "detect_goal_drift": true,
          "drift_threshold": 0.3
        },
        "memory_protection": {
          "enabled": true,
          "validate_memories": true,
          "max_memory_age_hours": 24,
          "detect_injection": true
        },
        "action_control": {
          "enabled": true,
          "allowed_actions": ["search", "calculate", "respond"],
          "blocked_actions": ["delete", "send_email", "execute_code"],
          "require_confirmation": ["purchase", "transfer"]
        },
        "loop_detection": {
          "enabled": true,
          "max_iterations": 10,
          "similarity_threshold": 0.9
        }
      }
    }
  ]
}
```

### Goal Drift Detection

```c
// Compare current goal with original
float drift = calculate_goal_drift(original_goal, current_goal);
if (drift > DRIFT_THRESHOLD) {
    log_alert("Goal drift detected: %.2f", drift);
    return ACTION_BLOCK;
}
```

---

## 6.5 Tool Guard

### Purpose

Control AI tool usage.

### Threats

| Threat | Description |
|--------|-------------|
| Unauthorized Access | Access to forbidden tools |
| Parameter Injection | Malicious parameters |
| Data Exfiltration | Data theft via tools |
| Resource Abuse | Resource misuse |

### Configuration

```json
{
  "guards": [
    {
      "type": "tool",
      "enabled": true,
      "config": {
        "tool_whitelist": {
          "enabled": true,
          "allowed": ["calculator", "weather", "search"],
          "blocked": ["shell", "file_write", "network"]
        },
        "parameter_validation": {
          "enabled": true,
          "sanitize_paths": true,
          "block_shell_chars": true,
          "max_param_length": 1024
        },
        "rate_limits": {
          "enabled": true,
          "per_tool": {
            "search": { "calls_per_minute": 10 },
            "api_call": { "calls_per_minute": 5 }
          }
        }
      }
    }
  ]
}
```

---

## 6.6 MCP Guard

### Purpose

Protect Model Context Protocol (Anthropic).

### Threats

| Threat | Description |
|--------|-------------|
| Context Manipulation | Context modification |
| Tool Injection | Malicious tool injection |
| Resource Hijacking | Resource capture |
| Prompt Injection | Through MCP messages |

### Configuration

```json
{
  "guards": [
    {
      "type": "mcp",
      "enabled": true,
      "config": {
        "server_validation": {
          "enabled": true,
          "allowed_servers": ["internal-mcp"],
          "verify_certificates": true
        },
        "tool_validation": {
          "enabled": true,
          "validate_schemas": true,
          "max_tools_per_request": 5
        },
        "resource_protection": {
          "enabled": true,
          "allowed_resources": ["docs/*", "data/*"],
          "blocked_resources": ["secrets/*", "config/*"]
        }
      }
    }
  ]
}
```

---

## 6.7 API Guard

### Purpose

Protect external API calls.

### Threats

| Threat | Description |
|--------|-------------|
| Data Exfiltration | Sending data externally |
| SSRF | Server-Side Request Forgery |
| Credential Exposure | Key leakage |
| Rate Abuse | DDoS via AI |

### Configuration

```json
{
  "guards": [
    {
      "type": "api",
      "enabled": true,
      "config": {
        "url_validation": {
          "enabled": true,
          "allowed_domains": ["api.openai.com", "internal.company.com"],
          "block_internal_ips": true,
          "block_localhost": true
        },
        "request_inspection": {
          "enabled": true,
          "check_body_for_secrets": true,
          "max_body_size": 1048576
        },
        "rate_limits": {
          "enabled": true,
          "requests_per_minute": 60
        }
      }
    }
  ]
}
```

### SSRF Prevention

```c
// Block internal IPs
if (is_internal_ip(target_ip)) {
    return ACTION_BLOCK;  // SSRF attempt
}

// Block localhost
if (is_localhost(url)) {
    return ACTION_BLOCK;
}

// Check allowed domains
if (!is_allowed_domain(url, allowed_domains)) {
    return ACTION_BLOCK;
}
```

---

## Practice

### Task 1

Configure LLM Guard for chatbot protection:
- Injection blocking
- DAN jailbreak detection
- Canary token for prompt leak

### Task 2

Create RAG Guard configuration for:
- Maximum 5 documents in context
- Source verification
- Hidden instruction removal

### Task 3

Write C code for Agent Guard integration:
- Goal drift detection
- Loop protection
- Action whitelist

---

## Module 6 Summary

- 6 Guards for different AI components
- Vtable interface for extensibility
- Each Guard — specific threats
- Configuration via JSON
- C API for integration

---

## Next Module

**Module 7: Protocols**

6 Shield protocols for enterprise.

---

_"Each Guard is a specialist in its domain."_
