# SENTINEL Shield API Reference

## Overview

This document describes the public C API for SENTINEL Shield.

---

## Core Functions

### Initialization

```c
#include "sentinel_shield.h"

// Initialize Shield context
shield_err_t shield_init(shield_context_t *ctx);

// Load configuration from file
shield_err_t shield_load_config(shield_context_t *ctx, const char *path);

// Destroy context and free resources
void shield_destroy(shield_context_t *ctx);
```

### Request Evaluation

```c
// Evaluation result
typedef struct {
    rule_action_t action;      // ALLOW, BLOCK, QUARANTINE, etc.
    char reason[256];          // Human-readable reason
    float threat_score;        // 0.0 - 1.0
    uint32_t matched_rule;     // Rule ID that matched
    int intent_type;           // Detected intent category
    float intent_confidence;   // Confidence of intent detection
} evaluation_result_t;

// Evaluate input
shield_err_t shield_evaluate(
    shield_context_t *ctx,
    const char *input,
    size_t input_len,
    const char *zone,
    rule_direction_t direction,
    evaluation_result_t *result
);
```

### Output Filtering

```c
// Filter output for sensitive content
shield_err_t shield_filter_output(
    shield_context_t *ctx,
    const char *output,
    size_t output_len,
    char *filtered,
    size_t *filtered_len
);

// Validate response
shield_err_t shield_validate_response(
    shield_context_t *ctx,
    const char *response,
    size_t len,
    validation_result_t *result
);
```

---

## Zone Management

```c
// Create a new zone
shield_err_t zone_create(zone_t *zone, const char *name, int trust_level);

// Register zone with context
shield_err_t shield_register_zone(shield_context_t *ctx, zone_t *zone);

// Find zone by name
zone_t *shield_find_zone(shield_context_t *ctx, const char *name);
```

---

## Rule Management

```c
// Create rule
shield_err_t rule_create(rule_t *rule);

// Set rule pattern
shield_err_t rule_set_pattern(rule_t *rule, const char *pattern, bool is_regex);

// Set rule action
void rule_set_action(rule_t *rule, rule_action_t action);

// Register rule
shield_err_t shield_register_rule(shield_context_t *ctx, rule_t *rule);
```

---

## Guards

```c
// Guard types
typedef enum {
    GUARD_TYPE_LLM,
    GUARD_TYPE_RAG,
    GUARD_TYPE_AGENT,
    GUARD_TYPE_TOOL,
    GUARD_TYPE_MCP,
    GUARD_TYPE_API,
} guard_type_t;

// Create guard
shield_err_t guard_create(guard_t *guard, guard_type_t type, const char *name);

// Register guard
shield_err_t shield_register_guard(shield_context_t *ctx, guard_t *guard);

// Invoke guard
shield_err_t guard_invoke(guard_t *guard, guard_event_t *event, guard_result_t *result);
```

---

## Semantic Analysis

```c
// Analyze text for intent
shield_err_t semantic_analyze(
    semantic_detector_t *detector,
    const char *text,
    size_t len,
    semantic_result_t *result
);

// Intent types
typedef enum {
    INTENT_BENIGN,
    INTENT_INSTRUCTION_OVERRIDE,
    INTENT_PROMPT_LEAK,
    INTENT_DATA_EXTRACTION,
    INTENT_JAILBREAK,
    INTENT_ROLEPLAY,
    INTENT_SOCIAL_ENGINEERING,
} intent_type_t;
```

---

## Encoding Detection

```c
// Detect encoding in text
shield_err_t detect_encoding(
    const char *text,
    size_t len,
    encoding_result_t *result
);

// Decode text recursively
char *decode_recursive(
    const char *text,
    size_t len,
    int max_layers,
    size_t *out_len
);
```

---

## Token Management

```c
// Estimate token count
int estimate_tokens(const char *text, size_t len, tokenizer_type_t type);

// Token budget
shield_err_t token_budget_init(token_budget_t *budget, int max_tokens);
bool token_budget_can_add(token_budget_t *budget, int tokens);
void token_budget_add(token_budget_t *budget, int tokens);
```

---

## Context Window

```c
// Initialize context window
shield_err_t context_window_init(context_window_t *ctx, int max_tokens);

// Add message
shield_err_t context_add_message(
    context_window_t *ctx,
    message_role_t role,
    const char *content,
    size_t len
);

// Set system prompt
shield_err_t context_set_system(context_window_t *ctx, const char *prompt);

// Export to JSON
char *context_to_json(context_window_t *ctx);
```

---

## Request Logging

```c
// Initialize logger
shield_err_t request_logger_init(request_logger_t *logger, const char *path);

// Log request
shield_err_t request_log(request_logger_t *logger, request_log_entry_t *entry);

// Query logs
int request_logger_query(
    request_logger_t *logger,
    uint64_t start_time,
    uint64_t end_time,
    const char *zone,
    rule_action_t action,
    request_log_entry_t **results,
    int max_results
);
```

---

## Metrics

```c
// Initialize metrics
shield_err_t metrics_init(metrics_t *metrics);

// Increment counter
void metrics_inc(metrics_t *metrics, const char *name);

// Set gauge
void metrics_set(metrics_t *metrics, const char *name, double value);

// Export to Prometheus format
char *metrics_to_prometheus(metrics_t *metrics);
```

---

## Error Codes

```c
typedef enum {
    SHIELD_OK = 0,
    SHIELD_ERR_INVALID = -1,
    SHIELD_ERR_NOMEM = -2,
    SHIELD_ERR_IO = -3,
    SHIELD_ERR_NOTFOUND = -4,
    SHIELD_ERR_EXISTS = -5,
    SHIELD_ERR_TIMEOUT = -6,
    SHIELD_ERR_UNSUPPORTED = -7,
    SHIELD_ERR_LIMIT = -8,
} shield_err_t;
```

---

## Thread Safety

All Shield functions are thread-safe when:

1. Each thread uses its own `shield_context_t`
2. Or access is synchronized externally

The thread pool and event bus provide concurrent processing.

---

## Memory Management

Shield uses memory pools for efficient allocation:

```c
// Create memory pool
shield_err_t mempool_create(mempool_t *pool, size_t block_size, int count);

// Allocate from pool
void *mempool_alloc(mempool_t *pool);

// Free to pool
void mempool_free(mempool_t *pool, void *ptr);
```

---

## Brain FFI

Shield can communicate with external AI analysis engines:

```c
#include "shield_brain.h"

// Initialize Brain connection
shield_err_t brain_ffi_init(const char *python_home, const char *brain_path);

// Check if Brain is available
bool brain_available(void);

// Analyze input for specific threat category
shield_err_t brain_ffi_analyze(
    const char *input,
    brain_engine_category_t category,
    brain_result_t *result
);

// Shutdown Brain connection
void brain_ffi_shutdown(void);
```

### Brain Categories

```c
typedef enum {
    BRAIN_ENGINE_INJECTION,      // Prompt injection
    BRAIN_ENGINE_JAILBREAK,      // Jailbreak attempts
    BRAIN_ENGINE_RAG_POISON,     // RAG poisoning
    BRAIN_ENGINE_AGENT_MANIP,    // Agent manipulation
    BRAIN_ENGINE_TOOL_HIJACK,    // Tool hijacking
    BRAIN_ENGINE_EXFILTRATION,   // Data exfiltration
} brain_engine_category_t;
```

---

## TLS/OpenSSL

Secure communication functions (requires `-DSHIELD_USE_OPENSSL`):

```c
#include "shield_tls.h"

// Initialize TLS context
shield_err_t tls_context_init(tls_context_t *ctx, const char *cert, const char *key);

// Create TLS-secured connection
shield_err_t tls_connect(tls_context_t *ctx, const char *host, int port);

// Read/write with TLS
ssize_t tls_read(tls_context_t *ctx, void *buf, size_t len);
ssize_t tls_write(tls_context_t *ctx, const void *buf, size_t len);

// Close connection
void tls_close(tls_context_t *ctx);
```

---

## See Also

- [Architecture Guide](ARCHITECTURE.md)
- [Configuration](CONFIGURATION.md)
- [Examples](../examples/)
- [Brain FFI Header](../include/shield_brain.h)
