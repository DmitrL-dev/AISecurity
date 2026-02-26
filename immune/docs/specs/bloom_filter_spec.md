# IMMUNE Bloom Filter — Specification

> **Version:** 1.0  
> **Author:** SENTINEL Team  
> **Date:** 2026-01-08  
> **Status:** Draft

---

## 1. Overview

### 1.1 Purpose

Accelerate pattern matching in IMMUNE Kmod using Bloom filters for fast rejection of non-matching inputs. Target: <1μs average latency for 10K+ patterns.

### 1.2 Problem Statement

From architecture critique (M1):
- 10K patterns × 100K syscalls/sec = CPU bottleneck
- Full regex matching on every input is expensive
- Need fast pre-filter to skip unlikely matches

### 1.3 Scope

| In Scope | Out of Scope |
|----------|--------------|
| Bloom filter data structure | Cuckoo filter |
| MurmurHash3 for hashing | Cryptographic hashes |
| Tiered matching pipeline | Kernel thread pool |
| SIMD optimization hints | Full AVX512 impl |

---

## 2. Requirements

### 2.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | Create Bloom filter with configurable size | P0 |
| FR-02 | Add patterns to filter | P0 |
| FR-03 | Check if input possibly matches any pattern | P0 |
| FR-04 | Tiered matching: Bloom → Hot Cache → Full | P0 |
| FR-05 | Rebuild filter on pattern update | P1 |
| FR-06 | Serialize/deserialize filter | P2 |

### 2.2 Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-01 | Bloom check latency | < 100ns |
| NFR-02 | Memory per filter | < 1MB for 10K patterns |
| NFR-03 | False positive rate | < 1% at 10K patterns |
| NFR-04 | Cache-friendly | Sequential memory access |

### 2.3 Performance Target

```
Bloom rejection rate: 95%
Average latency with Bloom: 100ns × 0.95 + 10μs × 0.05 = 595ns

vs. without Bloom: 10μs average

Speedup: ~17x
```

---

## 3. Architecture

### 3.1 Tiered Matching Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    MATCHING PIPELINE                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Input ───► [Bloom Filter] ───► "definitely not" ───► PASS │
│                   │                                          │
│                   ▼ (possibly match)                         │
│             [Hot Cache]  (top 100 patterns, LRU)            │
│                   │                                          │
│                   ▼ (cache miss)                             │
│             [Full Pattern Set]                               │
│                   │                                          │
│                   ▼                                          │
│              MATCH / NO MATCH                                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Bloom Filter Design

```
Parameters for 10K patterns, 1% FPR:
- m = 95,851 bits (~12KB)
- k = 7 hash functions
- Using MurmurHash3 with seeds 0..6

Memory layout:
┌──────────────────────────────────────┐
│ Header (16 bytes)                    │
│   - magic, version, m, k, count     │
├──────────────────────────────────────┤
│ Bit array (m/8 bytes)                │
│   - Sequential for cache efficiency │
└──────────────────────────────────────┘
```

### 3.3 Hash Function

Using MurmurHash3 with different seeds for k hash functions:
```
h1 = murmur3(data, seed=0) % m
h2 = murmur3(data, seed=1) % m
...
hk = murmur3(data, seed=k-1) % m
```

---

## 4. API Design

### 4.1 Data Types

```c
/* Bloom filter handle */
typedef struct bloom_filter bloom_filter_t;

/* Configuration */
typedef struct {
    size_t expected_items;      /* Expected number of items */
    double false_positive_rate; /* Desired FPR (default: 0.01) */
    int    hash_count;          /* Number of hash functions (0 = auto) */
} bloom_config_t;

/* Statistics */
typedef struct {
    size_t items;           /* Items added */
    size_t bits_set;        /* Bits set to 1 */
    double fill_ratio;      /* bits_set / total_bits */
    double estimated_fpr;   /* Actual FPR based on fill ratio */
} bloom_stats_t;
```

### 4.2 Functions

| Function | Description |
|----------|-------------|
| `bloom_create(config)` | Create new filter |
| `bloom_destroy(filter)` | Free filter |
| `bloom_add(filter, data, len)` | Add item to filter |
| `bloom_check(filter, data, len)` | Check if item possibly present |
| `bloom_clear(filter)` | Reset all bits |
| `bloom_stats(filter, stats)` | Get statistics |
| `bloom_save(filter, path)` | Serialize to file |
| `bloom_load(path)` | Deserialize from file |

---

## 5. Implementation Plan

### Phase 1: Core Bloom (0.5 day)
- [ ] bloom_filter.h header
- [ ] bloom_filter.c implementation
- [ ] MurmurHash3 integration

### Phase 2: Pipeline (0.5 day)
- [ ] Hot cache (LRU, top 100)
- [ ] Pipeline integration
- [ ] Pattern add/remove hooks

### Phase 3: Testing (0.5 day)
- [ ] Unit tests
- [ ] FPR verification
- [ ] Performance benchmarks

---

## 6. Test Plan

### 6.1 Unit Tests

| Test | Description |
|------|-------------|
| `test_create_destroy` | Create and free filter |
| `test_add_check` | Add item, check present |
| `test_not_present` | Not-added item not present |
| `test_fpr_measurement` | Measure actual FPR |
| `test_large_dataset` | 10K items, <1% FPR |
| `test_save_load` | Serialize/deserialize |

### 6.2 Performance Tests

| Test | Target |
|------|--------|
| Single check | < 100ns |
| Add 10K items | < 10ms |
| Load 12KB filter | < 1ms |

---

## 7. Acceptance Criteria

- [ ] Bloom check < 100ns average
- [ ] FPR < 1% at 10K patterns
- [ ] Memory < 1MB
- [ ] All unit tests pass
- [ ] Benchmark shows 10x+ speedup

---

*Document ready for implementation*
