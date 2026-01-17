# CI/CD Pipeline — Tasks

## Phase 1: GitHub Actions CI

- [x] **Task 1.1**: Создать `.github/workflows/ci.yml`
  - Python 3.11, 3.12 matrix
  - pytest with coverage
  - Upload to Codecov
  - Build package artifact

---

## Phase 2: Code Quality

- [x] **Task 2.1**: Создать `.github/workflows/lint.yml`
  - ruff linting
  - black formatting check
  - mypy type checking

---

## Phase 3: Security Scanning

- [x] **Task 3.1**: Создать `.github/workflows/security.yml`
  - Bandit security scan
  - Safety dependency check
  - pip-audit
  - CodeQL analysis

---

## Acceptance Criteria

| Критерий | Метрика | Статус |
|----------|---------|--------|
| ci.yml | pytest + coverage | ✅ |
| lint.yml | ruff + black + mypy | ✅ |
| security.yml | bandit + safety + CodeQL | ✅ |

---

**Created:** 2026-01-09
**Completed:** 2026-01-09
