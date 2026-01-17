# DB Migrations — Tasks

## Phase 1: Alembic Setup

- [x] **Task 1.1**: Создать `alembic.ini`
- [x] **Task 1.2**: Создать `migrations/env.py`
- [x] **Task 1.3**: Создать `migrations/script.py.mako`

---

## Phase 2: Models & Initial Migration

- [x] **Task 2.1**: Создать `src/brain/db/models.py`
  - AuditLog table
  - DetectionEvent table
  - APIKey table
  - EngineConfig table

- [x] **Task 2.2**: Создать initial migration
  - migrations/versions/001_initial.py
  - 4 tables with indexes

---

## Acceptance Criteria

| Критерий | Метрика | Статус |
|----------|---------|--------|
| alembic.ini | configured | ✅ |
| SQLAlchemy models | 4 tables | ✅ |
| Initial migration | 001_initial.py | ✅ |

---

**Created:** 2026-01-09
**Completed:** 2026-01-09
