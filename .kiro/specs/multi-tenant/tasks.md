# Phase 9: Multi-tenant & SaaS — Tasks

> **Phase:** 9
> **Version:** 1.0
> **Дата:** 2026-01-30

---

## Phase 9.1: Specification ✅ COMPLETE

- [x] requirements.md — APPROVED
- [x] design.md — APPROVED
- [x] tasks.md — APPROVED

---

## Phase 9.2: Tests First (TDD)

### 9.2.1 Unit Tests — TenantContext

- [ ] `test_set_tenant_context` — устанавливает app.tenant_id
- [ ] `test_tenant_context_isolation` — разные запросы изолированы
- [ ] `test_clear_tenant_context` — очистка после запроса

### 9.2.2 Unit Tests — RLS Policies

- [ ] `test_rls_blocks_cross_tenant` — нельзя видеть чужие данные
- [ ] `test_rls_allows_same_tenant` — видно свои данные
- [ ] `test_admin_bypass_rls` — админ видит всё

### 9.2.3 Unit Tests — UsageTracker

- [ ] `test_increment_api_calls` — счётчик API calls
- [ ] `test_increment_analyses` — счётчик analyses
- [ ] `test_flush_to_database` — сброс в БД
- [ ] `test_buffer_deduplication` — буфер не дублирует

### 9.2.4 Unit Tests — PlanLimits

- [ ] `test_community_limits` — 1000 analyses, 10 users
- [ ] `test_professional_limits` — 10000 analyses, 50 users
- [ ] `test_enterprise_unlimited` — no limits
- [ ] `test_limit_exceeded_error` — 429 при превышении

### 9.2.5 Unit Tests — API Keys

- [ ] `test_create_api_key` — создание ключа
- [ ] `test_validate_api_key` — проверка ключа
- [ ] `test_api_key_scopes` — ограничения по scope
- [ ] `test_api_key_rate_limit` — rate limiting

---

## Phase 9.3: Implementation ✅ COMPLETE

### 9.3.1 Schema Additions ✅

- [x] **usage.ts** — `usage_metrics` table
- [x] **api-keys.ts** — `tenant_api_keys` table
- [ ] **Drizzle migration** — generate + push (deferred)

### 9.3.2 RLS Setup

- [ ] **enable_rls.sql** — enable RLS on tables (deferred for PostgreSQL)
- [ ] **policies migration** — add tenant_id column where missing
- [ ] **Test RLS** — verify isolation

### 9.3.3 Middleware ✅

- [x] **tenant-context.ts** — TenantContext helper
- [x] **api-key-auth.ts** — API key validation
- [x] **usage-tracker.ts** — UsageTracker class
- [x] **plan-limits.ts** — Plan definitions

### 9.3.4 API Endpoints ✅

- [x] **GET /api/tenants** — list tenants
- [x] **POST /api/tenants** — create tenant
- [ ] **GET /api/tenants/:id** — get tenant (deferred)
- [ ] **GET /api/tenants/:id/members** — list members (deferred)
- [ ] **POST /api/tenants/:id/members** — invite member (deferred)
- [x] **GET /api/tenants/:id/usage** — usage stats
- [x] **GET /api/tenants/:id/api-keys** — list keys
- [x] **POST /api/tenants/:id/api-keys** — create key

### 9.3.5 Dashboard Components ✅

- [x] **TenantSelector.tsx** — tenant switcher
- [x] **UsageWidget.tsx** — usage display
- [ ] **ApiKeyManager.tsx** — key management (deferred)

---

## Phase 9.4: Verification

- [ ] All unit tests pass
- [ ] RLS isolation verified
- [ ] Usage tracking works
- [ ] Plan limits enforced
- [ ] Dashboard build passes
- [ ] Documentation updated

---

## Test Commands

```bash
# Unit tests
npm run test -- --grep "tenant"

# RLS test (manual)
psql -c "SET app.tenant_id = 'xxx'; SELECT * FROM policies;"
```

---

## Acceptance Criteria

| Критерий | Тест |
|----------|------|
| RLS isolation | `test_rls_blocks_cross_tenant` |
| Usage tracking | `test_flush_to_database` |
| Limit enforcement | `test_limit_exceeded_error` |
| API key validation | `test_validate_api_key` |
| 20+ unit tests | pytest/jest count |
