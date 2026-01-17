# Shield Metrics — Tasks

## Phase 1: Metrics Implementation

- [x] **Task 1.1**: Создать `shield/src/utils/metrics.h`
  - metric_type_t enum
  - metric_t, histogram_t structs
  - metrics_registry_t struct
  - Function declarations

- [x] **Task 1.2**: Создать `shield/src/utils/metrics.c`
  - metrics_init(), metrics_cleanup()
  - counter_register(), counter_inc(), counter_add()
  - gauge_register(), gauge_set(), gauge_inc/dec()
  - histogram_register(), histogram_observe()
  - metrics_export_prometheus()

---

## Phase 2: HTTP Endpoints

- [x] **Task 2.1**: handle_metrics_request()
  - Prometheus text format output
  - Content-Type: text/plain

- [x] **Task 2.2**: handle_health_request()
  - JSON health status
  - Component checks

---

## Phase 3: Default Metrics

- [x] **Task 3.1**: Default metrics registered
  - shield_requests_total
  - shield_requests_active
  - shield_auth_success_total
  - shield_auth_failure_total
  - shield_rate_limited_total
  - shield_request_duration_seconds (histogram)

---

## Acceptance Criteria

| Критерий | Метрика | Статус |
|----------|---------|--------|
| metrics.h | ~90 LOC | ✅ |
| metrics.c | ~280 LOC | ✅ |
| Prometheus format | ✓ | ✅ |

---

**Created:** 2026-01-09
**Completed:** 2026-01-09
