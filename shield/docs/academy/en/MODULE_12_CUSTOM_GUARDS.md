# SENTINEL Academy — Module 12

## Custom Guard Development

_SSE Level | Duration: 6 hours_

---

## Introduction

6 built-in Guards cover most use cases.

But sometimes specific logic is needed.

In this module — how to create your own Guard.

---

## 12.1 Guard Interface

### Vtable

Every Guard implements a vtable:

```c
// include/guards/guard_interface.h

typedef struct {
    // Identity
    const char *name;
    const char *version;
    guard_type_t type;

    // Lifecycle
    shield_err_t (*init)(const char *config_json, void **ctx);
    void (*destroy)(void *ctx);

    // Core
    shield_err_t (*evaluate)(void *ctx,
                              const guard_event_t *event,
                              guard_result_t *result);

    // Optional
    shield_err_t (*validate_config)(const char *config_json);
    void (*get_stats)(void *ctx, guard_stats_t *stats);
} guard_vtable_t;
```

### Events and Results

```c
typedef struct {
    const char *input;
    size_t input_len;
    const char *zone;
    direction_t direction;
    const char *session_id;
    const char *metadata;
} guard_event_t;

typedef struct {
    action_t action;           // ALLOW, BLOCK, LOG
    float threat_score;        // 0.0 - 1.0
    char reason[256];
    char details[1024];        // JSON
} guard_result_t;
```

---

## 12.2 Example: Rate Limit Guard

Create a Guard for per-session rate limiting.

### Header

```c
// include/guards/rate_limit_guard.h

#ifndef RATE_LIMIT_GUARD_H
#define RATE_LIMIT_GUARD_H

#include "guard_interface.h"

extern const guard_vtable_t rate_limit_guard_vtable;

typedef struct {
    int requests_per_minute;
    int burst_size;
    bool block_on_exceed;
} rate_limit_config_t;

#endif
```

### Implementation

```c
// src/guards/rate_limit_guard.c

typedef struct {
    rate_limit_config_t config;
    hash_table_t *sessions;
    pthread_mutex_t lock;
} rate_limit_ctx_t;

static shield_err_t rate_limit_init(const char *config_json, void **ctx) {
    rate_limit_ctx_t *rl = calloc(1, sizeof(rate_limit_ctx_t));
    parse_config(config_json, &rl->config);
    rl->sessions = hash_table_create(1024);
    pthread_mutex_init(&rl->lock, NULL);
    *ctx = rl;
    return SHIELD_OK;
}

static shield_err_t rate_limit_evaluate(void *ctx,
                                         const guard_event_t *event,
                                         guard_result_t *result) {
    rate_limit_ctx_t *rl = ctx;
    
    pthread_mutex_lock(&rl->lock);
    
    // Token bucket algorithm
    session_bucket_t *bucket = get_or_create_bucket(rl, event->session_id);
    
    if (bucket->tokens >= 1.0f) {
        bucket->tokens -= 1.0f;
        result->action = ACTION_ALLOW;
    } else {
        result->action = rl->config.block_on_exceed ? ACTION_BLOCK : ACTION_LOG;
        snprintf(result->reason, sizeof(result->reason), "Rate limit exceeded");
    }
    
    pthread_mutex_unlock(&rl->lock);
    return SHIELD_OK;
}

const guard_vtable_t rate_limit_guard_vtable = {
    .name = "rate_limit",
    .version = "1.0.0",
    .init = rate_limit_init,
    .destroy = rate_limit_destroy,
    .evaluate = rate_limit_evaluate,
};
```

---

## 12.3 Registration

### Adding to Guard Registry

```c
// src/guards/guard_registry.c

static const guard_vtable_t *builtin_guards[] = {
    &llm_guard_vtable,
    &rag_guard_vtable,
    &agent_guard_vtable,
    &tool_guard_vtable,
    &mcp_guard_vtable,
    &api_guard_vtable,
    &rate_limit_guard_vtable,  // Add here
    NULL
};
```

---

## 12.4 Configuration

### Config File

```json
{
  "guards": [
    {
      "type": "rate_limit",
      "enabled": true,
      "config": {
        "requests_per_minute": 60,
        "burst_size": 10,
        "block_on_exceed": true
      }
    }
  ]
}
```

---

## 12.5 Testing

### Unit Test

```c
void test_allows_within_limit(void) {
    guard_event_t event = {
        .input = "test",
        .session_id = "sess-1"
    };
    guard_result_t result;

    // Should allow first 5 (burst)
    for (int i = 0; i < 5; i++) {
        rate_limit_guard_vtable.evaluate(guard_ctx, &event, &result);
        TEST_ASSERT_EQUAL(ACTION_ALLOW, result.action);
    }
}

void test_blocks_over_limit(void) {
    guard_event_t event = {
        .input = "test",
        .session_id = "sess-2"
    };
    guard_result_t result;

    // Exhaust burst
    for (int i = 0; i < 5; i++) {
        rate_limit_guard_vtable.evaluate(guard_ctx, &event, &result);
    }

    // Next should block
    rate_limit_guard_vtable.evaluate(guard_ctx, &event, &result);
    TEST_ASSERT_EQUAL(ACTION_BLOCK, result.action);
}
```

---

## 12.6 Best Practices

### Thread Safety

```c
// Use mutex for shared state
pthread_mutex_lock(&ctx->lock);
// ... modify state ...
pthread_mutex_unlock(&ctx->lock);

// Or use atomics for simple counters
atomic_fetch_add(&ctx->count, 1);
```

### Memory Management

```c
// Allocate in init, free in destroy
static shield_err_t my_guard_init(const char *config, void **ctx) {
    my_ctx_t *my = calloc(1, sizeof(my_ctx_t));
    *ctx = my;
    return SHIELD_OK;
}

static void my_guard_destroy(void *ctx) {
    my_ctx_t *my = ctx;
    free(my->data);
    free(my);
}
```

### Performance

```c
// Avoid allocations in evaluate()
// Pre-allocate in init()

// Use pre-compiled patterns
// Cache expensive computations

// Early exit when possible
if (event->input_len == 0) {
    result->action = ACTION_ALLOW;
    return SHIELD_OK;
}
```

---

## Module 12 Summary

- Guard vtable interface
- Lifecycle: init/destroy/evaluate
- Registration in registry
- Configuration loading
- Testing

---

## Next Module

**Module 13: Plugin System**

Creating and loading external plugins.

---

_"Custom guards = custom protection."_
