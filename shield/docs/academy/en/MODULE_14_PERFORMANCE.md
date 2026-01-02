# SENTINEL Academy — Module 14

## Performance Engineering

_SSE Level | Duration: 4 hours_

---

## Benchmarking

### Built-in Benchmark

```bash
./shield-bench -n 100000 -v
```

### Results

```
Benchmark                    Avg (µs)    P99 (µs)    Ops/sec
─────────                    ────────    ────────    ───────
Basic Evaluation                0.85        1.20    1,176,470
Injection Detection             1.25        2.50      800,000
Large Payload (100KB)          12.50       25.00       80,000
Pattern Matching                0.45        0.80    2,222,222
```

---

## Profiling

### CPU

```bash
perf record ./shield -c config.json
perf report
```

### Memory

```bash
valgrind --tool=massif ./shield
ms_print massif.out.*
```

---

## Optimization Techniques

### Memory

- Use memory pools
- Avoid allocations in hot path
- Pre-allocate buffers

### CPU

- Compile regex to DFA
- Use SIMD for pattern matching
- Inline hot functions

### I/O

- Use io_uring on Linux
- Batch operations
- Async where possible

---

## Targets

| Metric | Target |
|--------|--------|
| Latency P99 | < 1ms |
| Throughput | 10K/s/core |
| Memory | < 100MB |

---

_"Performance is a feature."_
