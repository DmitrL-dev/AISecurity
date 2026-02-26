# SENTINEL Academy — Module 11

## Shield Internals

_SSE Level | Время: 6 часов_

---

## Введение

Добро пожаловать в SSE.

Ты изучишь как Shield работает изнутри.

Это даст понимание для:

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

### Component Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                         SHIELD                                │
│                                                              │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  │
│  │  Config   │  │  Logging  │  │  Metrics  │  │  Tracing  │  │
│  │  Manager  │  │  System   │  │  System   │  │  System   │  │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  │
│        │              │              │              │        │
│  ┌─────▼──────────────▼──────────────▼──────────────▼─────┐  │
│  │                    CONTEXT MANAGER                       │  │
│  │   (Session, Zone, Config, State)                        │  │
│  └────────────────────────┬────────────────────────────────┘  │
│                           │                                  │
│  ┌────────────────────────▼────────────────────────────────┐  │
│  │                   EVALUATION PIPELINE                   │  │
│  │                                                        │  │
│  │   ┌──────────┐   ┌──────────┐   ┌──────────┐          │  │
│  │   │Preprocessor│→│Rule Match │→│  Guards  │→ Result  │  │
│  │   └──────────┘   └──────────┘   └──────────┘          │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

## 11.2 Memory Management

### Memory Pools

Shield использует memory pools вместо malloc/free для:

- Предотвращения fragmentation
- Улучшения cache locality
- Предсказуемой latency

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

// Stats
memory_pool_stats_t stats;
memory_pool_get_stats(pool, &stats);
printf("Used: %zu/%zu\n", stats.used, stats.total);
```

### Arena Allocator

Для request-scoped memory:

```c
// Allocate arena for request
arena_t arena;
arena_init(&arena, 64 * 1024);  // 64KB

// All allocations during request use arena
char *copy = arena_strdup(&arena, input);
rule_result_t *results = arena_alloc(&arena, sizeof(rule_result_t) * 10);

// One free at end
arena_destroy(&arena);  // Frees everything
```

### Zero-Copy I/O

```c
// Buffer view without copying
typedef struct {
    const char *data;
    size_t len;
} buffer_view_t;

// Parse without copy
buffer_view_t get_json_field(buffer_view_t json, const char *key);
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

### Lock-Free Structures

```c
// Lock-free queue for work distribution
typedef struct {
    _Atomic(node_t*) head;
    _Atomic(node_t*) tail;
} lockfree_queue_t;

void queue_push(lockfree_queue_t *q, void *data);
void* queue_pop(lockfree_queue_t *q);
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
    uint32_t id;
    uint8_t priority;
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

### Pattern Cache

```c
// LRU cache for compiled patterns
typedef struct {
    hash_table_t *table;
    lru_list_t *lru;
    size_t max_size;
    pthread_rwlock_t lock;
} pattern_cache_t;

// Get or compile
compiled_pattern_t* cache_get(pattern_cache_t *cache, const char *pattern);
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

    // Conditions
    char zones[MAX_ZONES][64];
    int zone_count;
    direction_t direction;

    // Statistics
    _Atomic(uint64_t) match_count;
    _Atomic(uint64_t) eval_time_ns;
} rule_t;
```

### Rule Index

Fast lookup by zone:

```c
// Hash table: zone -> rule list
typedef struct {
    hash_table_t *zone_index;  // zone -> [rule_ids]
    rule_t *rules;             // rule array
    size_t rule_count;
} rule_index_t;

// Get rules for zone
void index_get_rules(rule_index_t *idx, const char *zone,
                     rule_t **rules, size_t *count);
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
            // Rule matched
            atomic_fetch_add(&rules[i].match_count, 1);

            if (rules[i].action == ACTION_BLOCK) {
                result->action = ACTION_BLOCK;
                result->threat_score = rules[i].severity / 10.0f;
                snprintf(result->reason, sizeof(result->reason),
                         "Rule: %s", rules[i].name);
                return SHIELD_OK;
            }
        }
    }

    result->action = ACTION_ALLOW;
    result->threat_score = 0.0f;
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
    EVENT_ERROR,
} event_type_t;

typedef struct {
    event_type_t type;
    uint64_t timestamp;
    char data[EVENT_DATA_SIZE];
} event_t;
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

### Ring Buffer for Events

```c
typedef struct {
    event_t *buffer;
    size_t size;
    _Atomic(size_t) head;
    _Atomic(size_t) tail;
} event_ring_t;

// Lock-free push
bool ring_push(event_ring_t *ring, const event_t *event);

// Lock-free pop
bool ring_pop(event_ring_t *ring, event_t *event);
```

---

## 11.7 Configuration System

### Config Loading

```c
// JSON parsing with arena allocator
config_t* config_load(const char *path, arena_t *arena) {
    // Read file
    char *json = read_file(path);

    // Parse
    json_value_t *root = json_parse(json, arena);

    // Validate
    if (!config_validate(root)) {
        return NULL;
    }

    // Convert to config struct
    config_t *config = arena_alloc(arena, sizeof(config_t));
    config_from_json(root, config);

    return config;
}
```

### Hot Reload

```c
// Watch config file
void config_watch(shield_context_t *ctx, const char *path) {
    int fd = inotify_init();
    inotify_add_watch(fd, path, IN_MODIFY);

    // In event loop
    if (event.type == INOTIFY_EVENT && event.mask & IN_MODIFY) {
        config_t *new_config = config_load(path, &arena);
        if (new_config) {
            config_swap(ctx, new_config);
            log_info("Config reloaded");
        }
    }
}
```

---

## 11.8 I/O Subsystem

### HTTP Server

```c
// Lightweight HTTP server
typedef struct {
    int fd;
    event_loop_t *loop;
    http_handler_t handler;
} http_server_t;

void http_server_start(http_server_t *server, int port) {
    server->fd = socket_listen(port);
    event_loop_add(server->loop, server->fd, EVENT_READ, on_accept);
}

static void on_accept(int fd, void *data) {
    http_server_t *server = data;
    int client = accept(fd, NULL, NULL);

    // Add to event loop
    http_conn_t *conn = pool_alloc(conn_pool);
    conn->fd = client;
    event_loop_add(server->loop, client, EVENT_READ, on_read);
}
```

### Request Parsing

```c
// Zero-copy HTTP parsing
typedef struct {
    buffer_view_t method;
    buffer_view_t path;
    buffer_view_t version;
    header_t headers[MAX_HEADERS];
    size_t header_count;
    buffer_view_t body;
} http_request_t;

int http_parse(const char *data, size_t len, http_request_t *req);
```

---

## Практика

### Задание 1

Реализуй memory pool:

- Fixed block size
- Bitmap для tracking
- Thread-safe

### Задание 2

Напиши Aho-Corasick для multiple pattern matching:

- Build automaton
- Search in O(n + m)

### Задание 3

Создай ring buffer:

- Lock-free push/pop
- Power-of-2 size

---

## Итоги Module 11

- Memory pools для performance
- Event loop architecture
- Pattern matching optimizations
- Rule engine internals
- Event bus system

---

## Следующий модуль

**Module 12: Custom Guard Development**

Создание собственных Guards.

---

_"To optimize, first understand."_
