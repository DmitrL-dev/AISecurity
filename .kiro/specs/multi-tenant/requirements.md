# Phase 9: Multi-tenant & SaaS — Requirements

> **Phase:** 9
> **Version:** 1.0
> **Дата:** 2026-01-30

---

## 1. Обзор

Multi-tenant архитектура для SaaS-версии SENTINEL:
- **Tenant isolation** — полная изоляция данных
- **Row-Level Security (RLS)** — PostgreSQL policies
- **Usage metering** — учёт использования API
- **Plan limits** — лимиты по тарифам

---

## 2. Functional Requirements

### FR-01: Tenant Management
- [ ] Создание tenant с уникальным slug
- [ ] Назначение owner при создании
- [ ] Invite members с ролями (owner, admin, member, viewer)
- [ ] Suspend/activate tenant

### FR-02: Row-Level Security
- [ ] Все таблицы с tenant_id защищены RLS
- [ ] Policies автоматически фильтруют по tenant
- [ ] API не может видеть чужие данные
- [ ] Admin bypass для супер-админов

### FR-03: Usage Metering
- [ ] Подсчёт API calls per tenant
- [ ] Подсчёт analyses per tenant
- [ ] Подсчёт blocked threats per tenant
- [ ] Monthly aggregation

### FR-04: Plan Limits
- [ ] Community: 1000 analyses/month, 10 users, 5 API keys
- [ ] Professional: 10000 analyses/month, 50 users, 20 API keys
- [ ] Enterprise: Unlimited

### FR-05: Billing Integration (Stub)
- [ ] Usage export endpoint
- [ ] Webhook for plan changes
- [ ] Stripe integration placeholder

---

## 3. Non-Functional Requirements

### NFR-01: Performance
- RLS overhead < 5ms per query
- Metering async (не блокирует API)
- Index on tenant_id для всех таблиц

### NFR-02: Security
- Tenant data never crosses boundaries
- Audit log per tenant
- API keys scoped to tenant

### NFR-03: Scalability
- Supports 1000+ tenants
- Horizontal scaling via Swarm

---

## 4. Existing Schema

### tenants.ts (Already Implemented)
```typescript
tenants {
  id, name, slug, plan
  settings, features
  maxUsers, maxApiKeys
  isActive, suspendedAt
}

tenantMembers {
  tenantId, userId, role
  invitedBy, invitedAt, acceptedAt
}
```

### Missing Tables
- [ ] `usage_metrics` — daily usage counters
- [ ] `tenant_api_keys` — API keys per tenant

---

## 5. RLS Policies

```sql
-- Example: policies table
ALTER TABLE policies ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON policies
  USING (tenant_id = current_setting('app.tenant_id')::uuid);

CREATE POLICY admin_bypass ON policies
  USING (current_setting('app.is_admin')::boolean = true);
```

---

## 6. User Stories

### US-01: Tenant onboarding
**Given** a new organization signs up
**When** they complete registration
**Then** a tenant is created with slug from company name

### US-02: Member invitation
**Given** a tenant admin
**When** they invite user@company.com
**Then** user receives invite email and can join tenant

### US-03: Usage visibility
**Given** a tenant owner
**When** they view Dashboard
**Then** they see current month usage and limits

### US-04: Limit enforcement
**Given** a Community tenant at 1000 analyses
**When** they try to analyze
**Then** they receive 429 with upgrade prompt

---

## 7. API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/tenants` | GET | List user's tenants |
| `/api/tenants` | POST | Create new tenant |
| `/api/tenants/:id` | GET | Get tenant details |
| `/api/tenants/:id/members` | GET | List members |
| `/api/tenants/:id/members` | POST | Invite member |
| `/api/tenants/:id/usage` | GET | Get usage stats |
| `/api/tenants/:id/api-keys` | GET/POST | Manage API keys |

---

## 8. Acceptance Criteria

| Критерий | Метрика |
|----------|---------|
| RLS isolation | 100% data separation |
| Usage tracking | ±1% accuracy |
| Limit enforcement | 0 overages |
| API overhead | < 10ms |
| Tests | 20+ unit tests |
