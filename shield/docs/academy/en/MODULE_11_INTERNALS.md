# SENTINEL Academy — Module 11

## Shield Internals

_SSE Level | Duration: 6 hours_

---

## Introduction

Welcome to SSE.

You'll learn how Shield works from the inside.

This gives understanding for:
- Performance optimization
- Custom development
- Debugging deep issues

---

## 11.1 Architecture Overview

### Layers

```
┌─────────────────────────────────────────────────────────────┐
│                        API LAYER                             │
│                    (HTTP/REST/CLI)                          │
├─────────────────────────────────────────────────────────────┤
│                     GUARD LAYER                              │
│              (LLM, RAG, Agent, Tool, MCP, API)              │
├─────────────────────────────────────────────────────────────┤
│                     RULE ENGINE                              │
│           (Pattern Matching, Semantic Analysis)             │
├─────────────────────────────────────────────────────────────┤
│                     CORE LAYER                               │
│      (Memory Pools, Threading, I/O, Event Loop)             │
├─────────────────────────────────────────────────────────────┤
│                   PROTOCOL LAYER                             │
│            (STP, SBP, ZDP, SHSP, SAF, SSRP)                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 11.2 Memory Management

### Memory Pools

Shield uses memory pools instead of malloc/free for:
- Preventing fragmentation
- Improving cache locality
- Predictable latency

```c
// include/core/memory.h

typedef struct {
    void *base;
    size_t block_size;
    size_t block_count;
    size_t free_count;
    uint64_t *bitmap;
} memory_pool_t;

// Create pool
memory_pool_t *pool;
memory_pool_create(1024, 10000, &pool);  // 1KB blocks, 10K blocks

// Allocate
void *ptr = memory_pool_alloc(pool);

// Free
memory_pool_free(pool, ptr);
```

### Arena Allocator

For request-scoped memory:

```c
// Allocate arena for request
arena_t arena;
arena_init(&arena, 64 * 1024);  // 64KB

// All allocations during request use arena
char *copy = arena_strdup(&arena, input);

// One free at end
arena_destroy(&arena);  // Frees everything
```

---

## 11.3 Threading Model

### Event Loop

Main thread runs event loop:

```c
void event_loop_run(event_loop_t *loop) {
    while (loop->running) {
        // Wait for events (epoll/kqueue)
        int n = event_wait(loop, events, MAX_EVENTS, timeout);

        for (int i = 0; i < n; i++) {
            handle_event(&events[i]);
        }

        // Process timers
        process_timers(loop);
    }
}
```

### Worker Pool

CPU-bound work offloaded to workers:

```c
// Thread pool
thread_pool_t *pool;
thread_pool_create(num_cores, &pool);

// Submit work
future_t future = thread_pool_submit(pool, evaluate_rule, &ctx);

// Wait for result
result_t result;
future_get(&future, &result, timeout);
```

---

## 11.4 Pattern Matching Engine

### Compilation

Patterns compiled at startup:

```c
typedef struct {
    pattern_type_t type;
    union {
        char *literal;         // LITERAL
        regex_t regex;         // REGEX
        semantic_model_t *ml;  // SEMANTIC
    } compiled;
} compiled_pattern_t;
```

### Matching Algorithm

```c
// Aho-Corasick for multiple literal patterns
// O(n + m) where n = input length, m = matches

typedef struct {
    int goto_table[MAX_STATES][ALPHABET_SIZE];
    int fail_table[MAX_STATES];
    int output_table[MAX_STATES];
} aho_corasick_t;

// Single pass matching
void ac_search(aho_corasick_t *ac, const char *text, match_callback cb);
```

---

## 11.5 Rule Engine

### Rule Representation

```c
typedef struct {
    uint32_t id;
    char name[64];

    // Matching
    compiled_pattern_t *pattern;

    // Actions
    action_t action;
    uint8_t severity;

    // Statistics
    _Atomic(uint64_t) match_count;
} rule_t;
```

### Evaluation

```c
shield_err_t evaluate_rules(shield_context_t *ctx,
                            const char *input, size_t len,
                            const char *zone,
                            evaluation_result_t *result) {
    // Get rules for zone
    rule_t *rules;
    size_t count;
    index_get_rules(&ctx->rule_index, zone, &rules, &count);

    // Evaluate in priority order
    for (size_t i = 0; i < count; i++) {
        match_result_t match;
        if (pattern_match(rules[i].pattern, input, len, &match)) {
            if (rules[i].action == ACTION_BLOCK) {
                result->action = ACTION_BLOCK;
                return SHIELD_OK;
            }
        }
    }

    result->action = ACTION_ALLOW;
    return SHIELD_OK;
}
```

---

## 11.6 Event System

### Event Types

```c
typedef enum {
    EVENT_REQUEST_RECEIVED,
    EVENT_REQUEST_ALLOWED,
    EVENT_REQUEST_BLOCKED,
    EVENT_RULE_MATCHED,
    EVENT_GUARD_TRIGGERED,
    EVENT_HA_FAILOVER,
    EVENT_CONFIG_RELOAD,
} event_type_t;
```

### Event Bus

```c
// Publish-subscribe pattern
typedef void (*event_handler_t)(const event_t *event, void *user_data);

// Subscribe
event_bus_subscribe(bus, EVENT_REQUEST_BLOCKED, handler, user_data);

// Publish
event_t event = {
    .type = EVENT_REQUEST_BLOCKED,
    .timestamp = time_now_ns()
};
event_bus_publish(bus, &event);
```

---

## Module 11 Summary

- Memory pools for performance
- Event loop architecture
- Pattern matching optimizations
- Rule engine internals
- Event bus system

---

## Next Module

**Module 12: Custom Guard Development**

Creating your own Guards.

---

_"To optimize, first understand."_
