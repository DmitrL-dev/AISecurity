# Phase 7: Database Migration — Tasks

> **Phase:** Phase 7 Dashboard V3
> **Статус:** ✅ Complete
> **Дата:** 2026-01-29

---

## Tasks

### Task 1: PostgreSQL Infrastructure ✅
- [x] 1.1 Docker-compose для PostgreSQL
- [x] 1.2 Добавить в .env.example

### Task 2: Extended Schema (Drizzle) ✅
- [x] 2.1 Drizzle ORM installed (Phase 6)
- [x] 2.2 `auth.ts` — userPreferences, apiKeys, authAudit (Phase 6)
- [x] 2.3 `tenants.ts` — tenant model, tenant_members
- [x] 2.4 `policies.ts` — security_policies, blocklist_entries
- [x] 2.5 `engines.ts` — engine_configs, engine_logs

### Task 3: Migrations ✅
- [x] 3.1 Добавить scripts в package.json
- [x] 3.2 drizzle.config.ts ready

### Task 4: Integration ✅
- [x] 4.1 Schema barrel export updated
- [x] 4.2 Build passes

---

## Acceptance Criteria

| Критерий | Статус |
|----------|--------|
| PostgreSQL docker-compose | ✅ |
| 8 Drizzle tables | ✅ |
| db:migrate script | ✅ |
| Build passes | ✅ |
