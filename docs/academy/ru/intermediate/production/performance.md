# ⚡ Урок 3.3: Performance Tuning

> **Время: 30 минут** | Mid-Level Module 3

---

## Performance Targets

| Tier | Latency | Engines |
|------|---------|---------|
| Tier 1 | <10ms | Pattern matching, keywords |
| Tier 2 | <50ms | Encoding, jailbreak |
| Tier 3 | <200ms | ML, TDA, complex |

---

## Caching Strategy

```rust
use sentinel_core::cache::RedisCache;

let cache = RedisCache::new(
    "redis://localhost:6379",
    300,   // 5 minutes TTL
    10000, // max_size
);

struct CachedEngine {
    cache: RedisCache,
}

impl CachedEngine {
    fn scan(&self, text: &str) -> ScanResult {
        // Check cache
        let cache_key = self.hash(text);
        if let Some(cached) = self.cache.get(&cache_key) {
            return cached;
        }

        // Compute
        let result = self.compute(text);

        // Store
        self.cache.set(&cache_key, &result);
        result
    }
}
```

---

## Tiered Execution

```rust
use sentinel_core::pipeline::TieredPipeline;

let pipeline = TieredPipeline::new(vec![
    Tier::new(tier1_engines.clone(), 10),  // timeout_ms
    Tier::new(tier2_engines.clone(), 50),
    Tier::new(tier3_engines.clone(), 200),
], true); // early_exit: Stop on first threat

let result = pipeline.scan(text);
```

---

## Parallel Execution

```rust
use tokio;
use futures::future::join_all;

async fn scan_parallel(text: &str, engines: &[Box<dyn BaseEngine>]) -> MergedResult {
    let tasks: Vec<_> = engines.iter()
        .map(|engine| engine.scan_async(text))
        .collect();
    let results = join_all(tasks).await;
    merge_results(&results)
}
```

---

## Benchmarking

```bash
# Run benchmark
sentinel benchmark --engines all --samples 1000

# Output:
# Engine                    | P50    | P95    | P99
# injection_detector        | 2ms    | 5ms    | 8ms
# jailbreak_detector        | 15ms   | 25ms   | 40ms
# tda_analyzer              | 80ms   | 150ms  | 200ms
```

---

## Следующий урок

→ [3.4: False Positive Reduction](./12-false-positive-reduction.md)
