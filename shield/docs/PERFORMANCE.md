# SENTINEL Shield Performance Tuning Guide

## Overview

SENTINEL Shield is designed for ultra-low latency operation. This guide covers tuning for optimal performance.

## Key Performance Metrics

| Metric        | Target     | Measurement                  |
| ------------- | ---------- | ---------------------------- |
| Latency (p50) | < 100μs    | Time from request to verdict |
| Latency (p99) | < 1ms      | Tail latency                 |
| Throughput    | > 100K rps | Requests per second          |
| Memory        | < 256MB    | Resident set size            |
| CPU           | < 10%      | Per core at 10K rps          |

## Configuration Tuning

### Thread Pool

```c
// Default: 4 threads
threadpool_init(&pool, CPU_COUNT);

// For high throughput
threadpool_init(&pool, CPU_COUNT * 2);
```

### Memory Pool

```c
// Pre-allocate for known workload
mempool_init(&pool, sizeof(request_t), 10000);
```

### Pattern Cache

```c
// Increase for many patterns
pattern_cache_init(&cache, 1000);  // 1000 cached patterns
```

### Rate Limiter

```c
// Token bucket tuning
ratelimit_init(&rl, 1000, 100);  // 1000 rps, burst 100
```

### Ring Buffer

```c
// For high-throughput event logging
ringbuf_init(&rb, 1024 * 1024);  // 1MB buffer
```

## Rule Optimization

### Rule Ordering

Place most-matched rules first:

```
access-list 100
  ! High-probability matches first
  shield-rule 10 block input llm contains "ignore"
  shield-rule 20 block input llm contains "disregard"
  ! Less common patterns later
  shield-rule 100 block input llm pattern "complex.*regex"
  ! Default allow last
  shield-rule 1000 allow input any
```

### Pattern Types

Performance ranking (fastest to slowest):

1. **EXACT** - O(1) hash lookup
2. **CONTAINS** - O(n) string search
3. **PREFIX/SUFFIX** - O(m) comparison
4. **REGEX** - O(n\*m) regex matching

Prefer `CONTAINS` over `REGEX` when possible.

### Blocklist

Use blocklist for exact matches instead of rules:

```c
// Fast O(1) lookup
blocklist_add(&bl, "password", "sensitive");
blocklist_check(&bl, text);  // Very fast
```

## Memory Optimization

### Session Cleanup

```c
// Aggressive session timeout
session_manager_init(&mgr, 60);  // 60 seconds

// Regular cleanup
session_cleanup(&mgr);
```

### Quarantine Limits

```c
// Limit quarantine size
quarantine_init(&mgr, 100, 3600);  // 100 items, 1 hour retention
```

### Pattern Cache LRU

```c
// Smaller cache = less memory
pattern_cache_init(&cache, 128);
```

## Network Optimization

### TCP Settings

```bash
# Linux sysctl
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.core.netdev_max_backlog = 65535
```

### Non-blocking I/O

Shield uses non-blocking sockets by default. Ensure:

```c
// Set socket options
int flags = fcntl(socket, F_GETFL, 0);
fcntl(socket, F_SETFL, flags | O_NONBLOCK);
```

## Profiling

### Built-in Metrics

```c
// Enable detailed metrics
metrics_enable_histograms(&metrics, true);
```

### Linux perf

```bash
perf record -g ./sentinel-shield
perf report
```

### Valgrind (development only)

```bash
valgrind --tool=callgrind ./sentinel-shield
```

## Benchmarking

### Local Benchmark

```c
// Build with -DBUILD_BENCHMARKS=ON
./bench_rule_engine
./bench_pattern_matching
```

### Load Testing

```bash
# Using wrk
wrk -t12 -c1000 -d30s http://localhost:8080/evaluate

# Using hey
hey -z 30s -c 1000 http://localhost:8080/evaluate
```

## Production Checklist

- [ ] Compile with `-O3 -DNDEBUG`
- [ ] Disable debug logging
- [ ] Pre-warm pattern cache
- [ ] Pre-allocate memory pools
- [ ] Configure appropriate thread count
- [ ] Set up CPU affinity
- [ ] Disable NUMA balancing if needed
- [ ] Monitor with Prometheus metrics

## Troubleshooting

### High Latency

1. Check rule count - too many rules slow evaluation
2. Simplify regex patterns
3. Increase pattern cache size
4. Profile with `perf`

### Memory Growth

1. Check session timeout
2. Verify quarantine cleanup
3. Monitor pattern cache size
4. Check for memory leaks with Valgrind

### CPU Spikes

1. Check regex complexity
2. Reduce logging
3. Increase rate limits
4. Add more threads
