# API Versioning — Tasks

## Phase 1: Router Structure

- [x] **Task 1.1**: Создать `src/brain/api/v1/__init__.py`
  - APIRouter for v1
  - Include analyze, health, engines routers

- [x] **Task 1.2**: Создать `src/brain/api/v1/analyze.py`
  - POST /v1/analyze (Pydantic models)
  - POST /v1/analyze/stream (SSE)
  - POST /v1/analyze/batch

- [x] **Task 1.3**: Создать `src/brain/api/v1/health.py`
  - GET /v1/health
  - GET /v1/health/ready
  - GET /v1/health/live

- [x] **Task 1.4**: Создать `src/brain/api/v1/engines.py`
  - GET /v1/engines
  - GET /v1/engines/{name}
  - GET /v1/engines/{name}/stats

---

## Acceptance Criteria

| Критерий | Метрика | Статус |
|----------|---------|--------|
| /v1/ prefix | All endpoints | ✅ |
| Pydantic models | Request/Response | ✅ |
| Files created | 4 | ✅ |

---

**Created:** 2026-01-09
**Completed:** 2026-01-09
