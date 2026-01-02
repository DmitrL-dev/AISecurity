# SENTINEL Academy — Module 12

## Custom Guard Development

_SSE Level | Время: 6 часов_

---

## Введение

6 built-in Guards покрывают большинство use cases.

Но иногда нужна специфичная логика.

В этом модуле — как создать свой Guard.

---

## 12.1 Guard Interface

### Vtable

Каждый Guard реализует vtable:

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
    void (*reset_stats)(void *ctx);
    const char* (*get_description)(void);
} guard_vtable_t;
```

### Events и Results

```c
typedef struct {
    // Input
    const char *input;
    size_t input_len;

    // Context
    const char *zone;
    direction_t direction;
    const char *session_id;
    const char *user_id;
    uint64_t timestamp;

    // Metadata (JSON)
    const char *metadata;
} guard_event_t;

typedef struct {
    action_t action;           // ALLOW, BLOCK, LOG, SANITIZE
    float threat_score;        // 0.0 - 1.0
    char reason[256];
    char details[1024];        // JSON
    uint64_t eval_time_ns;
} guard_result_t;
```

---

## 12.2 Example: Rate Limit Guard

Создадим Guard для rate limiting на уровне session.

### Header

```c
// include/guards/rate_limit_guard.h

#ifndef RATE_LIMIT_GUARD_H
#define RATE_LIMIT_GUARD_H

#include "guard_interface.h"

// Export vtable
extern const guard_vtable_t rate_limit_guard_vtable;

// Config
typedef struct {
    int requests_per_minute;
    int burst_size;
    bool block_on_exceed;
} rate_limit_config_t;

// Stats
typedef struct {
    uint64_t total_requests;
    uint64_t rate_limited;
    uint64_t blocked;
} rate_limit_stats_t;

#endif
```

### Implementation

```c
// src/guards/rate_limit_guard.c

#include "guards/rate_limit_guard.h"
#include "core/hash_table.h"
#include "core/time.h"
#include <stdlib.h>
#include <string.h>

// Per-session state
typedef struct {
    int64_t tokens;
    uint64_t last_update;
} session_bucket_t;

// Guard context
typedef struct {
    rate_limit_config_t config;
    hash_table_t *sessions;  // session_id -> bucket
    pthread_mutex_t lock;
    rate_limit_stats_t stats;
} rate_limit_ctx_t;

// === Lifecycle ===

static shield_err_t rate_limit_init(const char *config_json, void **ctx) {
    rate_limit_ctx_t *rl = calloc(1, sizeof(rate_limit_ctx_t));
    if (!rl) return SHIELD_ERR_MEMORY;

    // Parse config
    if (!parse_config(config_json, &rl->config)) {
        free(rl);
        return SHIELD_ERR_CONFIG;
    }

    // Initialize sessions hash table
    rl->sessions = hash_table_create(1024);
    pthread_mutex_init(&rl->lock, NULL);

    *ctx = rl;
    return SHIELD_OK;
}

static void rate_limit_destroy(void *ctx) {
    rate_limit_ctx_t *rl = ctx;

    // Free all buckets
    hash_table_foreach(rl->sessions, free_bucket, NULL);
    hash_table_destroy(rl->sessions);

    pthread_mutex_destroy(&rl->lock);
    free(rl);
}

// === Core Logic ===

static shield_err_t rate_limit_evaluate(void *ctx,
                                         const guard_event_t *event,
                                         guard_result_t *result) {
    rate_limit_ctx_t *rl = ctx;
    uint64_t now = time_now_ms();

    pthread_mutex_lock(&rl->lock);

    // Get or create bucket
    session_bucket_t *bucket = hash_table_get(rl->sessions, event->session_id);
    if (!bucket) {
        bucket = calloc(1, sizeof(session_bucket_t));
        bucket->tokens = rl->config.burst_size;
        bucket->last_update = now;
        hash_table_put(rl->sessions, event->session_id, bucket);
    }

    // Token bucket algorithm
    uint64_t elapsed = now - bucket->last_update;
    float tokens_to_add = elapsed * rl->config.requests_per_minute / 60000.0f;
    bucket->tokens = MIN(bucket->tokens + tokens_to_add, rl->config.burst_size);
    bucket->last_update = now;

    rl->stats.total_requests++;

    // Check limit
    if (bucket->tokens >= 1.0f) {
        bucket->tokens -= 1.0f;

        result->action = ACTION_ALLOW;
        result->threat_score = 0.0f;
    } else {
        rl->stats.rate_limited++;

        if (rl->config.block_on_exceed) {
            result->action = ACTION_BLOCK;
            result->threat_score = 0.5f;
            snprintf(result->reason, sizeof(result->reason),
                     "Rate limit exceeded");
            rl->stats.blocked++;
        } else {
            result->action = ACTION_LOG;
            result->threat_score = 0.3f;
        }
    }

    pthread_mutex_unlock(&rl->lock);
    return SHIELD_OK;
}

// === Optional ===

static shield_err_t rate_limit_validate_config(const char *json) {
    rate_limit_config_t config;
    if (!parse_config(json, &config)) {
        return SHIELD_ERR_CONFIG;
    }
    if (config.requests_per_minute <= 0) {
        return SHIELD_ERR_CONFIG;
    }
    return SHIELD_OK;
}

static void rate_limit_get_stats(void *ctx, guard_stats_t *stats) {
    rate_limit_ctx_t *rl = ctx;

    snprintf(stats->data, sizeof(stats->data),
             "{\"total\": %llu, \"limited\": %llu, \"blocked\": %llu}",
             rl->stats.total_requests,
             rl->stats.rate_limited,
             rl->stats.blocked);
}

static const char* rate_limit_description(void) {
    return "Per-session rate limiting using token bucket algorithm";
}

// === Vtable Export ===

const guard_vtable_t rate_limit_guard_vtable = {
    .name = "rate_limit",
    .version = "1.0.0",
    .type = GUARD_TYPE_CUSTOM,

    .init = rate_limit_init,
    .destroy = rate_limit_destroy,
    .evaluate = rate_limit_evaluate,

    .validate_config = rate_limit_validate_config,
    .get_stats = rate_limit_get_stats,
    .get_description = rate_limit_description,
};
```

---

## 12.3 Registration

### Adding to Guard Registry

```c
// src/guards/guard_registry.c

#include "guards/guard_registry.h"
#include "guards/llm_guard.h"
#include "guards/rag_guard.h"
// ...
#include "guards/rate_limit_guard.h"  // Your guard

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

void guard_registry_init(guard_registry_t *registry) {
    for (int i = 0; builtin_guards[i] != NULL; i++) {
        guard_registry_add(registry, builtin_guards[i]);
    }
}
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

### Loading

```c
// In shield_load_config
for (int i = 0; i < config->guard_count; i++) {
    guard_config_t *gc = &config->guards[i];

    const guard_vtable_t *vtable = guard_registry_find(registry, gc->type);
    if (!vtable) {
        log_error("Unknown guard type: %s", gc->type);
        continue;
    }

    void *guard_ctx;
    shield_err_t err = vtable->init(gc->config_json, &guard_ctx);
    if (err != SHIELD_OK) {
        log_error("Failed to init guard %s: %d", gc->type, err);
        continue;
    }

    // Add to evaluation chain
    shield_add_guard(ctx, vtable, guard_ctx);
}
```

---

## 12.5 Testing

### Unit Test

```c
// tests/test_rate_limit_guard.c

#include "unity.h"
#include "guards/rate_limit_guard.h"

static void *guard_ctx;

void setUp(void) {
    const char *config = "{\"requests_per_minute\": 60, \"burst_size\": 5, \"block_on_exceed\": true}";
    shield_err_t err = rate_limit_guard_vtable.init(config, &guard_ctx);
    TEST_ASSERT_EQUAL(SHIELD_OK, err);
}

void tearDown(void) {
    rate_limit_guard_vtable.destroy(guard_ctx);
}

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

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_allows_within_limit);
    RUN_TEST(test_blocks_over_limit);
    return UNITY_END();
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
    // ...
    *ctx = my;
    return SHIELD_OK;
}

static void my_guard_destroy(void *ctx) {
    my_ctx_t *my = ctx;
    // Free all owned resources
    free(my->data);
    free(my);
}
```

### Error Handling

```c
static shield_err_t my_guard_evaluate(void *ctx, ...) {
    // Validate inputs
    if (!ctx || !event || !result) {
        return SHIELD_ERR_INVALID_ARG;
    }

    // Safe defaults for result
    result->action = ACTION_ALLOW;
    result->threat_score = 0.0f;
    result->reason[0] = '\0';

    // ... evaluation logic ...

    return SHIELD_OK;
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

## 12.7 Complex Example: PII Guard

```c
// Simplified PII detection guard

typedef struct {
    regex_t email_regex;
    regex_t phone_regex;
    regex_t ssn_regex;
    bool redact;
} pii_guard_ctx_t;

static shield_err_t pii_evaluate(void *ctx,
                                  const guard_event_t *event,
                                  guard_result_t *result) {
    pii_guard_ctx_t *pii = ctx;

    bool has_email = regex_match(&pii->email_regex, event->input);
    bool has_phone = regex_match(&pii->phone_regex, event->input);
    bool has_ssn = regex_match(&pii->ssn_regex, event->input);

    if (has_ssn) {
        result->action = ACTION_BLOCK;
        result->threat_score = 0.9f;
        snprintf(result->reason, sizeof(result->reason),
                 "SSN detected in input");
    } else if (has_email || has_phone) {
        result->action = pii->redact ? ACTION_SANITIZE : ACTION_LOG;
        result->threat_score = 0.5f;
        snprintf(result->reason, sizeof(result->reason),
                 "PII detected: email=%d phone=%d", has_email, has_phone);
    } else {
        result->action = ACTION_ALLOW;
        result->threat_score = 0.0f;
    }

    return SHIELD_OK;
}
```

---

## Практика

### Задание 1

Создай Geo Guard:

- Блокировка по IP geolocation
- Whitelist/blacklist стран
- Config: blocked_countries, allowed_countries

### Задание 2

Создай Content Guard:

- Обнаружение toxicity
- Severity levels
- Regex + keyword matching

### Задание 3

Напиши unit tests:

- 5+ test cases
- Edge cases
- Config validation

---

## Итоги Module 12

- Guard vtable interface
- Lifecycle: init/destroy/evaluate
- Registration in registry
- Configuration loading
- Testing

---

## Следующий модуль

**Module 13: Plugin System**

Создание и загрузка external plugins.

---

_"Custom guards = custom protection."_
