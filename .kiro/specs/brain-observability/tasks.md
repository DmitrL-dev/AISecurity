# Brain Observability — Tasks

## Phase 1: Prometheus Metrics

- [x] **Task 1.1**: Создать `src/brain/observability/__init__.py`

- [x] **Task 1.2**: Создать `observability/metrics.py`
  - MetricsRegistry class
  - Counter, Histogram, Gauge wrappers
  - request_count, request_latency metrics
  - engine_*, cache_*, detections_* metrics
  - @timed decorator

---

## Phase 2: Health Checks

- [x] **Task 2.1**: Создать `observability/health.py`
  - HealthCheck class
  - HealthStatus enum
  - ComponentHealth, HealthResult dataclasses
  - check_all(), check_ready(), check_live()
  - Default probes: brain, redis, engines

---

## Phase 3: Tracing (optional)

- [ ] **Task 3.1**: Создать `observability/tracing.py`
  - OpenTelemetry integration (future)

---

## Acceptance Criteria

| Критерий | Метрика | Статус |
|----------|---------|--------|
| metrics.py | ~290 LOC | ✅ |
| health.py | ~210 LOC | ✅ |
| All imports working | 100% | ✅ |

---

**Created:** 2026-01-09
**Completed:** 2026-01-09
