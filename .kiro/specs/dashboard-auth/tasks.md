# Dashboard Auth — Tasks

> **Фаза:** Phase 6 Dashboard V3
> **Статус:** ✅ Phase 6 Complete
> **Дата:** 2026-01-29

---

## Чеклист имплементации

### Task 1: Keycloak Setup ✅
- [x] 1.1 Создать `keycloak/docker-compose.yml`
- [x] 1.2 Настроить realm "sentinel" с OIDC
- [x] 1.3 Создать клиент "sentinel-dashboard"
- [x] 1.4 Настроить роли: admin, analyst, viewer, api-only
- [x] 1.5 Включить TOTP для 2FA (conditional для admin)
- [x] 1.6 Создать тестовых пользователей
- [x] 1.7 Экспортировать realm config (`realm-sentinel.json`)

### Task 2: NextAuth Integration ✅
- [x] 2.1 Установить `next-auth@beta` (v5)
- [x] 2.2 Создать `src/lib/auth.ts` с Keycloak provider
- [x] 2.3 Создать `src/app/api/auth/[...nextauth]/route.ts`
- [x] 2.4 Настроить callbacks (jwt, session) для roles
- [x] 2.5 Добавить SessionProvider (`AuthProvider.tsx`)
- [x] 2.6 Настроить HttpOnly cookies

### Task 3: RBAC Middleware ✅
- [x] 3.1 Создать `src/lib/rbac.ts` с permission definitions
- [x] 3.2 Создать `src/middleware.ts` для route protection
- [x] 3.3 Тестировать доступ по ролям (включено в middleware)

### Task 4: API Protection ✅
- [x] 4.1 Создать `src/lib/api-auth.ts` с withAuth helper
- [x] 4.2 Применить protection ко всем API routes (ready to use)
- [x] 4.3 Добавить role checks (withAdmin, withAnalyst helpers)

### Task 5: UI Components ✅
- [x] 5.1 Создать `LoginButton.tsx`
- [x] 5.2 Создать `RoleGuard.tsx`
- [x] 5.3 Создать `UserMenu.tsx` (header dropdown)
- [x] 5.4 Создать `/login` page
- [x] 5.5 Создать `/unauthorized` page
- [x] 5.6 Обновить Header с auth state (ready to integrate)

### Task 6: Database Schema ✅
- [x] 6.1 Создать миграцию для `user_preferences`
- [x] 6.2 Создать миграцию для `api_keys`
- [x] 6.3 Создать миграцию для `auth_audit`
- [x] 6.4 Добавить индексы (via Drizzle relations)

### Task 7: Audit Logging ✅
- [x] 7.1 Логировать login events (`logLogin`)
- [x] 7.2 Логировать logout events (`logLogout`)
- [x] 7.3 Логировать failed login attempts (`logLoginFailed`)
- [x] 7.4 Логировать role-based access denials (`logAccessDenied`)

### Task 8: Testing ✅
- [x] 8.1 Unit tests для RBAC logic (`rbac.test.ts`)
- [x] 8.2 Integration tests для auth flow (`auth.test.ts`, `api-auth.test.ts`)
- [x] 8.3 E2E tests с Playwright (`e2e/auth/login.spec.ts`, `protected-routes.spec.ts`, `rbac.spec.ts`)
- [x] 8.4 Manual testing checklist (in docs)

### Task 9: Documentation ✅
- [x] 9.1 README для Keycloak setup
- [x] 9.2 Environment variables documentation
- [x] 9.3 RBAC roles guide (`docs/auth-rbac.md`)

---

## Приоритеты

| Приоритет | Tasks |
|-----------|-------|
| **P0 (Critical)** | 1.1-1.6, 2.1-2.6, 3.1-3.2 |
| **P1 (High)** | 4.1-4.3, 5.1-5.6 |
| **P2 (Medium)** | 6.1-6.4, 7.1-7.4 |
| **P3 (Low)** | 8.1-8.4, 9.1-9.3 |

---

## Зависимости

```
Task 1 (Keycloak) ──► Task 2 (NextAuth)
                            │
                            ▼
                    Task 3 (RBAC) ──► Task 4 (API)
                            │
                            ▼
                    Task 5 (UI)
                            │
                            ▼
                    Task 6 (DB) ──► Task 7 (Audit)
                            │
                            ▼
                    Task 8 (Testing)
                            │
                            ▼
                    Task 9 (Docs)
```

---

## Estimated Effort

| Task | Время |
|------|-------|
| Task 1 | 2-3 часа |
| Task 2 | 2-3 часа |
| Task 3 | 1-2 часа |
| Task 4 | 1-2 часа |
| Task 5 | 2-3 часа |
| Task 6 | 1 час |
| Task 7 | 1-2 часа |
| Task 8 | 2-3 часа |
| Task 9 | 1 час |
| **Total** | **13-20 часов** |
