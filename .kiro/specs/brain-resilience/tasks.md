# Brain Resilience — Tasks

## Phase 1: Redis Cache

- [x] **Task 1.1**: Создать `src/brain/core/cache.py`
  - CacheConfig dataclass
  - MemoryCache class (LRU)
  - RedisCache class
  - HybridCache (Redis + Memory fallback)
  - get_cache() singleton
  - cache_key() helper

---

## Phase 2: Circuit Breaker

- [x] **Task 2.1**: Создать `src/brain/core/resilience.py`
  - CircuitState enum (CLOSED/OPEN/HALF_OPEN)
  - CircuitConfig dataclass
  - CircuitBreaker class
  - retry_with_backoff() async helper
  - @circuit_breaker decorator
  - with_fallback() helper

---

## Phase 3: Streaming Response

- [x] **Task 3.1**: Создать `src/brain/api/streaming.py`
  - StreamEvent dataclass (SSE format)
  - StreamingAnalyzer class
  - create_streaming_response() helper
  - heartbeat_generator()

---

## Acceptance Criteria

| Критерий | Метрика | Статус |
|----------|---------|--------|
| core/cache.py | ~280 LOC | ✅ |
| core/resilience.py | ~250 LOC | ✅ |
| api/streaming.py | ~220 LOC | ✅ |
| All imports working | 100% | ✅ |

---

**Created:** 2026-01-09
**Completed:** 2026-01-09
