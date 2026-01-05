# SENTINEL Academy — Module 14

## Performance Engineering

_SSE Level | Duration: 6 hours_

---

## Introduction

Shield must work with latency < 1ms.

In this module — how to achieve and maintain that goal.

---

## 14.1 Performance Goals

| Metric | Target | Acceptable |
|--------|--------|------------|
| P50 latency | < 0.5ms | < 1ms |
| P99 latency | < 1ms | < 5ms |
| P99.9 latency | < 5ms | < 10ms |
| Throughput | > 10K RPS | > 5K RPS |
| Memory | < 256MB | < 512MB |

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
```

---

## 14.3 Memory Optimization

### Memory Pools

```c
typedef struct {
    memory_pool_t *small;   // 64 bytes
    memory_pool_t *medium;  // 512 bytes
    memory_pool_t *large;   // 4096 bytes
} pool_set_t;

void* pool_alloc(pool_set_t *ps, size_t size) {
    if (size <= 64) return memory_pool_alloc(ps->small);
    if (size <= 512) return memory_pool_alloc(ps->medium);
    if (size <= 4096) return memory_pool_alloc(ps->large);
    return malloc(size);  // Fallback
}
```

### Arena per Request

```c
void handle_request(request_t *req) {
    arena_t arena;
    arena_init(&arena, 32 * 1024);  // 32KB

    // All allocations use arena
    parsed_input_t *parsed = arena_alloc(&arena, sizeof(parsed_input_t));

    // Single free at end
    arena_destroy(&arena);
}
```

---

## 14.4 Pattern Matching Optimization

### Aho-Corasick for Multiple Patterns

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

---

## 14.5 I/O Optimization

### Non-blocking I/O

```c
// Use epoll (Linux) / kqueue (BSD/macOS)
int epfd = epoll_create1(0);

struct epoll_event ev = {
    .events = EPOLLIN | EPOLLET,  // Edge-triggered
    .data.fd = client_fd
};
epoll_ctl(epfd, EPOLL_CTL_ADD, client_fd, &ev);
```

### Buffer Reuse

```c
// Thread-local buffers
static __thread char read_buf[65536];
static __thread char write_buf[65536];

void handle_connection(int fd) {
    ssize_t n = read(fd, read_buf, sizeof(read_buf));
    // Process using read_buf
    write(fd, write_buf, response_len);
}
```

---

## 14.6 Cache Optimization

### Rule Cache

```c
typedef struct {
    uint64_t input_hash;
    action_t action;
    float threat_score;
    uint64_t timestamp;
} cached_result_t;

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

---

## 14.7 Benchmarking

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

---

## 14.8 Performance Checklist

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

---

## Module 14 Summary

- Profiling tools
- Memory optimization
- Pattern matching optimization
- I/O and threading
- Caching strategies
- Benchmarking

---

## Next Module

**Module 15: Capstone Project**

Final SSE project.

---

_"Premature optimization is the root of all evil. But mature optimization is the root of all performance."_
