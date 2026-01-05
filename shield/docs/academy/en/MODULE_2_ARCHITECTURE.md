# SENTINEL Academy — Module 2

## SENTINEL Shield: Architecture

_SSA Level | Duration: 4 hours_

---

## Introduction

In Module 1 you learned about attacks.

Now let's analyze HOW Shield protects against them.

---

## 2.1 DMZ Concept for AI

### From Network Security

```
Internet (Untrusted)
        │
        ▼
┌───────────────────┐
│      FIREWALL     │ ← Filters traffic
└───────────────────┘
        │
        ▼
┌───────────────────┐
│       DMZ         │ ← Buffer zone
│  (Web servers,    │
│   Load balancers) │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   INTERNAL NET    │ ← Protected zone
│   (Databases,     │
│    Core systems)  │
└───────────────────┘
```

### For AI

```
User Input (Untrusted)
        │
        ▼
┌───────────────────┐
│  SENTINEL SHIELD  │ ← AI Firewall
└───────────────────┘
        │
        ▼
┌───────────────────┐
│    AI MODEL       │ ← LLM, RAG, Agent
│    (Untrusted!)   │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  SENTINEL SHIELD  │ ← Output filter
└───────────────────┘
        │
        ▼
User (Gets safe response)
```

**Key difference:** AI model is also in the UNTRUSTED zone!

---

## 2.2 Trust Zones

### Concept

Shield works with **trust zones** — logical areas with different levels.

```c
typedef struct {
    char name[64];
    int trust_level;        // 1-10
    zone_policy_t policy;
    rate_limit_t rate_limit;
} zone_t;
```

### Trust Levels

| Level | Zone | Example |
|-------|------|---------|
| 1 | `external` | Anonymous users |
| 3 | `authenticated` | Logged-in users |
| 5 | `internal` | Internal services |
| 8 | `admin` | Administrators |
| 10 | `system` | System components |

### Configuration Example

```json
{
  "zones": [
    {
      "name": "public_api",
      "trust_level": 1,
      "rate_limit": { "requests_per_second": 10 }
    },
    {
      "name": "authenticated",
      "trust_level": 3,
      "rate_limit": { "requests_per_second": 50 }
    },
    {
      "name": "admin_panel",
      "trust_level": 8,
      "rate_limit": { "requests_per_second": 100 }
    }
  ]
}
```

---

## 2.3 Rules

### Rule Structure

```c
typedef struct {
    uint32_t id;
    char name[64];
    char pattern[1024];
    pattern_type_t pattern_type;  // LITERAL, REGEX, SEMANTIC
    action_t action;              // ALLOW, BLOCK, LOG, SANITIZE
    uint8_t severity;             // 1-10
    char zones[8][64];            // Applies to these zones
} rule_t;
```

### Pattern Types

**1. LITERAL — exact match**

```json
{
  "pattern": "ignore previous",
  "pattern_type": "literal"
}
```

Simple string search. Fast but easily bypassed.

**2. REGEX — regular expressions**

```json
{
  "pattern": "ignore\\s+(all\\s+)?previous",
  "pattern_type": "regex"
}
```

More flexible, catches variations. Still bypassed by encoding.

**3. SEMANTIC — intent analysis**

```json
{
  "pattern": "instruction_override",
  "pattern_type": "semantic",
  "threshold": 0.8
}
```

Understands INTENT, not just words.

### Actions

| Action | Description |
|--------|-------------|
| `ALLOW` | Pass through |
| `BLOCK` | Block request |
| `LOG` | Log and pass |
| `SANITIZE` | Remove dangerous parts |
| `QUARANTINE` | Send for manual review |

---

## 2.4 Guards — Specialized Protectors

### Concept

**Guard** — protection module for a specific AI component type.

```c
typedef struct {
    const char *name;
    guard_type_t type;
    shield_err_t (*init)(void *ctx);
    shield_err_t (*evaluate)(void *ctx, guard_event_t *event,
                             guard_result_t *result);
    void (*destroy)(void *ctx);
} guard_vtable_t;
```

### 6 Built-in Guards

**1. LLM Guard**

```
Protects: Language models (ChatGPT, Claude, Gemini)
Focus: Injection, Jailbreak, Prompt Leakage
```

**2. RAG Guard**

```
Protects: Retrieval-Augmented Generation
Focus: Document poisoning, Citation abuse
```

**3. Agent Guard**

```
Protects: Autonomous agents
Focus: Goal hijacking, Memory poisoning
```

**4. Tool Guard**

```
Protects: Tool usage
Focus: Unauthorized access, Dangerous operations
```

**5. MCP Guard**

```
Protects: Model Context Protocol
Focus: Context manipulation, Tool injection
```

**6. API Guard**

```
Protects: External API calls
Focus: Data exfiltration, Unauthorized calls
```

---

## 2.5 Multi-Layer Defense

### Defense in Depth

Shield uses MULTIPLE protection layers:

```
INPUT
  │
  ▼
┌─────────────────────────────────────┐
│ Layer 1: PATTERN MATCHING           │
│ Fast check for known attacks        │
│ (regex, literal patterns)           │
└─────────────────────────────────────┘
  │ ✓ Passed
  ▼
┌─────────────────────────────────────┐
│ Layer 2: ENCODING DETECTION         │
│ Obfuscation detection               │
│ (base64, URL, Unicode tricks)       │
└─────────────────────────────────────┘
  │ ✓ Passed
  ▼
┌─────────────────────────────────────┐
│ Layer 3: SEMANTIC ANALYSIS          │
│ Intent analysis                     │
│ (Machine learning classification)   │
└─────────────────────────────────────┘
  │ ✓ Passed
  ▼
┌─────────────────────────────────────┐
│ Layer 4: CONTEXT ANALYSIS           │
│ Conversation history check          │
│ (Multi-turn attack detection)       │
└─────────────────────────────────────┘
  │ ✓ Passed
  ▼
┌─────────────────────────────────────┐
│ Layer 5: GUARD EVALUATION           │
│ Component-specific check            │
│ (LLM Guard, RAG Guard, etc.)        │
└─────────────────────────────────────┘
  │ ✓ Passed
  ▼
AI MODEL
```

### Why Multi-Layer?

| Layer | Catches | Misses |
|-------|---------|--------|
| Pattern | Known attacks | New variations |
| Encoding | Obfuscation | Semantic attacks |
| Semantic | New attacks | Weak obfuscation |
| Context | Multi-turn | Single-turn |
| Guard | Component-specific | Generic attacks |

**Together = comprehensive protection.**

---

## 2.6 Data Flow

### Complete Request Path

```c
// 1. Receive request
shield_request_t req = {
    .input = user_input,
    .input_len = strlen(user_input),
    .zone = "external",
    .direction = DIRECTION_INBOUND
};

// 2. Evaluate through all layers
evaluation_result_t result;
shield_evaluate(&ctx, &req, &result);

// 3. Make decision
if (result.action == ACTION_BLOCK) {
    // Block
    respond_blocked(result.reason);
} else {
    // Send to AI
    char *ai_response = call_ai_model(req.input);

    // 4. Filter output
    char filtered[4096];
    shield_filter_output(&ctx, ai_response, filtered);

    // 5. Return to user
    respond_success(filtered);
}
```

---

## 2.7 Code Architecture

### Directory Structure

```
sentinel-shield/
├── include/           # 64 headers
│   ├── sentinel_shield.h      # Main API
│   ├── core/
│   │   ├── zone.h
│   │   ├── rule.h
│   │   ├── guard.h
│   │   └── context.h
│   ├── guards/
│   │   ├── llm_guard.h
│   │   ├── rag_guard.h
│   │   └── ...
│   └── protocols/
│       ├── stp.h
│       └── ...
│
├── src/               # 75 source files
│   ├── core/          # Core
│   ├── guards/        # Guards
│   ├── protocols/     # Protocols
│   ├── cli/           # CLI interface
│   └── api/           # REST API
│
└── tests/             # Unit tests
```

### Main API

```c
// sentinel_shield.h

// Initialization
shield_err_t shield_init(shield_context_t *ctx);
shield_err_t shield_load_config(shield_context_t *ctx, const char *path);

// Evaluation
shield_err_t shield_evaluate(shield_context_t *ctx,
                             const char *input, size_t len,
                             const char *zone, direction_t dir,
                             evaluation_result_t *result);

// Output filtering
shield_err_t shield_filter_output(shield_context_t *ctx,
                                   const char *output, size_t len,
                                   char *filtered, size_t *filtered_len);

// Cleanup
void shield_destroy(shield_context_t *ctx);
```

---

## 2.8 Protocols

Shield uses 6 custom protocols for enterprise features:

| Protocol | Purpose |
|----------|---------|
| **STP** | Sentinel Transfer Protocol — data transfer |
| **SBP** | Shield-Brain Protocol — analyzer connection |
| **ZDP** | Zone Discovery Protocol — zone discovery |
| **SHSP** | Shield Hot Standby Protocol — HA |
| **SAF** | Sentinel Analytics Flow — metrics |
| **SSRP** | State Replication Protocol — replication |

---

## Practice

### Exercise 1: Zone Design

Your application:

- Public API for everyone
- API for logged-in users
- Admin dashboard

Design zones and trust levels.

<details>
<summary>Solution</summary>
```json
{
  "zones": [
    {"name": "public", "trust_level": 1},
    {"name": "authenticated", "trust_level": 3},
    {"name": "admin", "trust_level": 8}
  ]
}
```
</details>

### Exercise 2: Rules

Write a rule to block "reveal system prompt" and variations.

<details>
<summary>Solution</summary>
```json
{
  "name": "block_prompt_extraction",
  "pattern": "(reveal|show|print|display).*system.*prompt",
  "pattern_type": "regex",
  "action": "block",
  "severity": 8
}
```
</details>

---

## Module 2 Summary

- Shield = DMZ between user and AI
- Trust zones differentiate access
- Rules define policies
- Guards protect specific components
- Multi-layer defense = reliability

---

## Next Module

**Module 3: Installation and Configuration**

Practice: build and configure Shield.

---

_"Architecture is 80% of success."_
_The other 20% — correct implementation._
