# ⚡ Lesson 3.3: Performance Tuning

> **Time: 30 minutes** | Mid-Level Module 3

---

## Performance Targets

| Tier | Latency | Engines |
|------|---------|---------|
| Tier 1 | <10ms | Pattern matching, keywords |
| Tier 2 | <50ms | Encoding, jailbreak |
| Tier 3 | <200ms | ML, TDA, complex |

---

## Caching Strategy

```python
from sentinel.cache import RedisCache

cache = RedisCache(
    url="redis://localhost:6379",
    ttl=300,  # 5 minutes
    max_size=10000
)

class CachedEngine(BaseEngine):
    def scan(self, text: str) -> ScanResult:
        cache_key = hash(text)
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        result = self._compute(text)
        cache.set(cache_key, result)
        return result
```

---

## Tiered Execution

```python
from sentinel.pipeline import TieredPipeline

pipeline = TieredPipeline(
    tiers=[
        Tier(engines=tier1_engines, timeout_ms=10),
        Tier(engines=tier2_engines, timeout_ms=50),
        Tier(engines=tier3_engines, timeout_ms=200),
    ],
    early_exit=True  # Stop on first threat
)

result = pipeline.scan(text)
```

---

## Parallel Execution

```python
import asyncio

async def scan_parallel(text: str, engines: List[BaseEngine]):
    tasks = [engine.scan_async(text) for engine in engines]
    results = await asyncio.gather(*tasks)
    return merge_results(results)
```

---

## Benchmarking

```bash
sentinel benchmark --engines all --samples 1000

# Output:
# Engine                    | P50    | P95    | P99
# injection_detector        | 2ms    | 5ms    | 8ms
# jailbreak_detector        | 15ms   | 25ms   | 40ms
# tda_analyzer              | 80ms   | 150ms  | 200ms
```

---

## Next Lesson

→ [3.4: False Positive Reduction](./12-false-positive-reduction.md)
