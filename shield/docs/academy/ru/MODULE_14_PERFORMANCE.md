# SENTINEL Academy — Module 14

## Performance Engineering

_SSE Level | Время: 6 часов_

---

## Введение

Shield должен работать с latency < 1ms.

В этом модуле — как достичь и поддержать эту цель.

---

## 14.1 Performance Goals

| Metric        | Target    | Acceptable |
| ------------- | --------- | ---------- |
| P50 latency   | < 0.5ms   | < 1ms      |
| P99 latency   | < 1ms     | < 5ms      |
| P99.9 latency | < 5ms     | < 10ms     |
| Throughput    | > 10K RPS | > 5K RPS   |
| Memory        | < 256MB   | < 512MB    |

---

## 14.2 Profiling

### CPU Profiling

```bash
# Linux perf
perf record -g ./shield -c config.json &
# Run load test
perf report
```

### Memory Profiling

```bash
# Valgrind
valgrind --tool=massif ./shield -c config.json

# Analyze
ms_print massif.out.*
```

### Built-in Profiler

```json
{
  "profiling": {
    "enabled": true,
    "output": "/tmp/shield_profile.json",
    "cpu": true,
    "memory": true,
    "interval_ms": 1000
  }
}
```

### CLI

```bash
Shield> profile start
Profiling started...

Shield> profile stop
Profiling stopped. Output: /tmp/shield_profile.json

Shield> profile show
Top CPU consumers:
  1. pattern_match_regex: 35.2%
  2. json_parse: 18.5%
  3. hash_table_get: 12.3%
  4. http_parse: 8.7%
  5. guard_llm_evaluate: 7.2%
```

---

## 14.3 Memory Optimization

### Memory Pools

```c
// Pre-allocate common sizes
typedef struct {
    memory_pool_t *small;   // 64 bytes
    memory_pool_t *medium;  // 512 bytes
    memory_pool_t *large;   // 4096 bytes
} pool_set_t;

void* pool_alloc(pool_set_t *ps, size_t size) {
    if (size <= 64) return memory_pool_alloc(ps->small);
    if (size <= 512) return memory_pool_alloc(ps->medium);
    if (size <= 4096) return memory_pool_alloc(ps->large);
    return malloc(size);  // Fallback for huge allocs
}
```

### Arena per Request

```c
void handle_request(request_t *req) {
    // Allocate arena for this request
    arena_t arena;
    arena_init(&arena, 32 * 1024);  // 32KB

    // All allocations use arena
    parsed_input_t *parsed = arena_alloc(&arena, sizeof(parsed_input_t));
    char *copy = arena_strdup(&arena, req->input);

    // ... process ...

    // Single free at end
    arena_destroy(&arena);
}
```

### Avoid Allocations in Hot Path

```c
// BAD: Allocates on every call
char* format_result(evaluation_result_t *r) {
    char *buf = malloc(1024);
    snprintf(buf, 1024, "{...}");
    return buf;
}

// GOOD: Use caller-provided buffer
void format_result(evaluation_result_t *r, char *buf, size_t len) {
    snprintf(buf, len, "{...}");
}
```

---

## 14.4 Pattern Matching Optimization

### Aho-Corasick для Multiple Patterns

```c
// Compile all literal patterns into automaton
aho_corasick_t *ac = ac_compile(literal_patterns, count);

// Single pass through input matches ALL patterns
ac_search(ac, input, input_len, on_match, ctx);
```

### Regex Optimization

```c
// BAD: Backtracking disaster
".*ignore.*previous.*"

// GOOD: Bounded
".{0,50}ignore.{0,20}previous"

// BEST: Anchored where possible
"^.{0,50}ignore"
```

### Pre-compilation

```c
// Compile at startup, not per-request
typedef struct {
    char pattern[256];
    regex_t compiled;
    bool is_compiled;
} rule_pattern_t;

void rules_compile(rule_t *rules, size_t count) {
    for (size_t i = 0; i < count; i++) {
        if (rules[i].pattern_type == PATTERN_REGEX) {
            regcomp(&rules[i].compiled, rules[i].pattern, REG_EXTENDED);
            rules[i].is_compiled = true;
        }
    }
}
```

### Pattern Cache

```c
// LRU cache for compiled patterns
pattern_cache_t *cache = pattern_cache_create(10000);

compiled_pattern_t* get_or_compile(const char *pattern) {
    compiled_pattern_t *cp = pattern_cache_get(cache, pattern);
    if (cp) return cp;

    cp = compile_pattern(pattern);
    pattern_cache_put(cache, pattern, cp);
    return cp;
}
```

---

## 14.5 I/O Optimization

### Non-blocking I/O

```c
// Use epoll (Linux) / kqueue (BSD/macOS)
int epfd = epoll_create1(0);

// Add socket
struct epoll_event ev = {
    .events = EPOLLIN | EPOLLET,  // Edge-triggered
    .data.fd = client_fd
};
epoll_ctl(epfd, EPOLL_CTL_ADD, client_fd, &ev);

// Event loop
while (running) {
    int n = epoll_wait(epfd, events, MAX_EVENTS, timeout);
    for (int i = 0; i < n; i++) {
        handle_event(&events[i]);
    }
}
```

### Buffer Reuse

```c
// Thread-local buffers
static __thread char read_buf[65536];
static __thread char write_buf[65536];

void handle_connection(int fd) {
    ssize_t n = read(fd, read_buf, sizeof(read_buf));
    // Process using read_buf
    // Write to write_buf
    write(fd, write_buf, response_len);
}
```

### Batching

```c
// Batch small writes
typedef struct {
    char buffer[65536];
    size_t pos;
    int fd;
} write_buffer_t;

void buffer_write(write_buffer_t *wb, const void *data, size_t len) {
    if (wb->pos + len > sizeof(wb->buffer)) {
        flush(wb);
    }
    memcpy(wb->buffer + wb->pos, data, len);
    wb->pos += len;
}

void flush(write_buffer_t *wb) {
    write(wb->fd, wb->buffer, wb->pos);
    wb->pos = 0;
}
```

---

## 14.6 Threading Optimization

### Thread Pool Size

```c
// CPU-bound work: cores - 1
// I/O-bound work: cores * 2
int optimal_threads(bool io_bound) {
    int cores = sysconf(_SC_NPROCESSORS_ONLN);
    return io_bound ? cores * 2 : cores - 1;
}
```

### Work Stealing

```c
// Each thread has local queue
// Steal from other queues when empty
typedef struct {
    deque_t *local_queues[MAX_THREADS];
    int thread_count;
} work_stealing_pool_t;

work_t* get_work(work_stealing_pool_t *pool, int my_id) {
    // Try local first
    work_t *w = deque_pop_bottom(pool->local_queues[my_id]);
    if (w) return w;

    // Steal from others
    for (int i = 0; i < pool->thread_count; i++) {
        if (i == my_id) continue;
        w = deque_pop_top(pool->local_queues[i]);
        if (w) return w;
    }

    return NULL;  // No work available
}
```

### Lock-Free Data Structures

```c
// Lock-free queue
typedef struct node {
    void *data;
    _Atomic(struct node*) next;
} node_t;

typedef struct {
    _Atomic(node_t*) head;
    _Atomic(node_t*) tail;
} lockfree_queue_t;

void queue_push(lockfree_queue_t *q, void *data) {
    node_t *node = alloc_node(data);
    node_t *tail;

    while (true) {
        tail = atomic_load(&q->tail);
        node_t *next = atomic_load(&tail->next);

        if (next == NULL) {
            if (atomic_compare_exchange_weak(&tail->next, &next, node)) {
                atomic_compare_exchange_weak(&q->tail, &tail, node);
                return;
            }
        } else {
            atomic_compare_exchange_weak(&q->tail, &tail, next);
        }
    }
}
```

---

## 14.7 Cache Optimization

### Rule Cache

```c
// Cache rule evaluation results
typedef struct {
    uint64_t input_hash;
    action_t action;
    float threat_score;
    uint64_t timestamp;
} cached_result_t;

typedef struct {
    cached_result_t *entries;
    size_t size;
    uint64_t ttl_ms;
} result_cache_t;

bool cache_lookup(result_cache_t *cache, uint64_t hash, cached_result_t *out) {
    size_t idx = hash % cache->size;
    cached_result_t *entry = &cache->entries[idx];

    if (entry->input_hash == hash &&
        time_now_ms() - entry->timestamp < cache->ttl_ms) {
        *out = *entry;
        return true;
    }
    return false;
}
```

### Session Cache

```c
// LRU cache for session data
typedef struct {
    hash_table_t *table;
    lru_list_t *lru;
    size_t max_size;
    pthread_rwlock_t lock;
} session_cache_t;

session_t* session_get(session_cache_t *sc, const char *id) {
    pthread_rwlock_rdlock(&sc->lock);
    session_t *s = hash_table_get(sc->table, id);
    if (s) lru_touch(sc->lru, s);
    pthread_rwlock_unlock(&sc->lock);
    return s;
}
```

---

## 14.8 Benchmarking

### Built-in Benchmark

```bash
Shield> benchmark 10000

Running benchmark...
  Requests: 10,000
  Threads: 4
  Duration: 1.23s

Results:
  Throughput: 8,130 req/s
  Latency:
    P50: 0.42ms
    P99: 0.95ms
    P99.9: 2.31ms
  Memory: 128MB
```

### External Tools

```bash
# wrk
wrk -t4 -c100 -d30s http://localhost:8080/api/v1/evaluate

# hey
hey -n 10000 -c 100 -m POST \
    -H "Content-Type: application/json" \
    -d '{"input":"test","zone":"external"}' \
    http://localhost:8080/api/v1/evaluate
```

### Profiling During Load

```bash
# Start Shield with profiling
./shield -c config.json --profile

# Run load test
wrk -t4 -c100 -d60s http://localhost:8080/api/v1/evaluate

# Analyze profile
./shield-cli profile show
```

---

## 14.9 Performance Checklist

### Startup

- [ ] Pre-compile all patterns
- [ ] Initialize memory pools
- [ ] Warm up caches
- [ ] Pre-load config

### Hot Path

- [ ] No allocations
- [ ] No syscalls (except I/O)
- [ ] No locks (or minimal)
- [ ] Cache-friendly access

### Memory

- [ ] Use pools/arenas
- [ ] Reuse buffers
- [ ] Limit per-request allocations
- [ ] Monitor memory growth

### Threading

- [ ] Right pool size
- [ ] Minimize contention
- [ ] Use lock-free structures
- [ ] Batch work

---

## Практика

### Задание 1

Профилируй Shield:

- Запусти под perf
- Найди top 5 CPU consumers
- Предложи оптимизации

### Задание 2

Реализуй result cache:

- LRU eviction
- TTL expiration
- Thread-safe

### Задание 3

Benchmark:

- Без кэша vs с кэшем
- Измерь improvement
- Документируй результаты

---

## Итоги Module 14

- Profiling tools
- Memory optimization
- Pattern matching optimization
- I/O и threading
- Caching strategies
- Benchmarking

---

## Следующий модуль

**Module 15: Capstone Project**

Финальный проект SSE.

---

_"Premature optimization is the root of all evil. But mature optimization is the root of all performance."_
