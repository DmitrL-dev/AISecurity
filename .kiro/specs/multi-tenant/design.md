# Phase 9: Multi-tenant & SaaS — Design

> **Phase:** 9
> **Version:** 1.0
> **Дата:** 2026-01-30

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                       MULTI-TENANT LAYER                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Tenant A   │    │   Tenant B   │    │   Tenant C   │      │
│  │              │    │              │    │              │      │
│  │ • 5 users    │    │ • 50 users   │    │ • unlimited  │      │
│  │ • Community  │    │ • Pro        │    │ • Enterprise │      │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘      │
│         │                   │                   │               │
│         └───────────────────┴───────────────────┘               │
│                             │                                   │
│                   ┌─────────▼─────────┐                        │
│                   │   RLS Policies    │                        │
│                   │  (tenant_id = ?)  │                        │
│                   └─────────┬─────────┘                        │
│                             │                                   │
│                   ┌─────────▼─────────┐                        │
│                   │    PostgreSQL     │                        │
│                   │   (shared DB)     │                        │
│                   └───────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Design

### 2.1 TenantContext Middleware

Sets tenant context for each request.

```typescript
// lib/tenant-context.ts
export async function withTenantContext<T>(
  tenantId: string,
  callback: () => Promise<T>
): Promise<T> {
  await db.execute(sql`SELECT set_config('app.tenant_id', ${tenantId}, true)`);
  return callback();
}
```

### 2.2 Usage Metrics Schema

```typescript
// db/schema/usage.ts
export const usageMetrics = pgTable("usage_metrics", {
  id: uuid("id").primaryKey().defaultRandom(),
  tenantId: uuid("tenant_id").references(() => tenants.id).notNull(),
  date: date("date").notNull(),
  
  // Counters
  apiCalls: integer("api_calls").default(0),
  analyses: integer("analyses").default(0),
  blockedThreats: integer("blocked_threats").default(0),
  
  // Metadata
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});
```

### 2.3 Tenant API Keys

```typescript
// db/schema/api-keys.ts
export const tenantApiKeys = pgTable("tenant_api_keys", {
  id: uuid("id").primaryKey().defaultRandom(),
  tenantId: uuid("tenant_id").references(() => tenants.id).notNull(),
  name: varchar("name", { length: 100 }).notNull(),
  keyHash: varchar("key_hash", { length: 64 }).notNull(), // SHA-256
  keyPrefix: varchar("key_prefix", { length: 8 }).notNull(), // sk_live_xxxx
  
  // Permissions
  scopes: jsonb("scopes").default(["analyze"]),
  rateLimit: integer("rate_limit").default(1000), // per hour
  
  // Status
  isActive: boolean("is_active").default(true),
  lastUsedAt: timestamp("last_used_at"),
  expiresAt: timestamp("expires_at"),
  
  createdAt: timestamp("created_at").defaultNow(),
  createdBy: uuid("created_by"),
});
```

### 2.4 Plan Limits

```typescript
// lib/plan-limits.ts
export const PLAN_LIMITS = {
  community: {
    analysesPerMonth: 1000,
    maxUsers: 10,
    maxApiKeys: 5,
    features: ["basic_engines"],
  },
  professional: {
    analysesPerMonth: 10000,
    maxUsers: 50,
    maxApiKeys: 20,
    features: ["basic_engines", "advanced_engines", "api_access"],
  },
  enterprise: {
    analysesPerMonth: Infinity,
    maxUsers: Infinity,
    maxApiKeys: Infinity,
    features: ["basic_engines", "advanced_engines", "api_access", "sso", "audit"],
  },
} as const;
```

---

## 3. RLS Implementation

### 3.1 Enable RLS on Tables

```sql
-- Migration: enable_rls.sql

-- Policies table
ALTER TABLE policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE policies FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policies ON policies
  FOR ALL
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Engine configs
ALTER TABLE engine_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE engine_configs FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_engines ON engine_configs
  FOR ALL
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Usage metrics
ALTER TABLE usage_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_metrics FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_usage ON usage_metrics
  FOR ALL  
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
```

### 3.2 Bypass for Admin

```sql
CREATE POLICY admin_all_access ON policies
  FOR ALL
  TO sentinel_admin
  USING (true);
```

---

## 4. File Structure

```
dashboard/src/
├── lib/
│   ├── tenant-context.ts    # Tenant middleware
│   ├── plan-limits.ts       # Plan definitions
│   ├── usage-tracker.ts     # Metering
│   └── api-key-auth.ts      # API key validation
├── db/schema/
│   ├── usage.ts             # Usage metrics
│   └── api-keys.ts          # Tenant API keys
├── app/api/
│   ├── tenants/
│   │   ├── route.ts         # CRUD
│   │   └── [id]/
│   │       ├── route.ts
│   │       ├── members/route.ts
│   │       ├── usage/route.ts
│   │       └── api-keys/route.ts
│   └── ...
└── components/
    ├── TenantSelector.tsx
    ├── UsageWidget.tsx
    └── ApiKeyManager.tsx
```

---

## 5. Middleware Flow

```
Request → Auth Check → Tenant Resolution → RLS Context → Handler
                │               │               │
                │               │               └─ SET app.tenant_id
                │               │
                │               └─ From session/API key
                │
                └─ NextAuth / API Key
```

---

## 6. Usage Tracking

### Async Metering Pipeline

```typescript
// lib/usage-tracker.ts
export class UsageTracker {
  private buffer: Map<string, UsageIncrement> = new Map();
  
  increment(tenantId: string, type: 'api_call' | 'analysis' | 'blocked') {
    // Buffer locally, flush to DB every 10s
    const key = `${tenantId}:${type}`;
    const current = this.buffer.get(key) || 0;
    this.buffer.set(key, current + 1);
  }
  
  async flush() {
    // Batch upsert to usage_metrics
    for (const [key, count] of this.buffer) {
      const [tenantId, type] = key.split(':');
      await this.upsertUsage(tenantId, type, count);
    }
    this.buffer.clear();
  }
}
```

---

## 7. Error Handling

| Scenario | Response |
|----------|----------|
| No tenant context | 401 Unauthorized |
| Tenant suspended | 403 Forbidden + reason |
| Plan limit exceeded | 429 Too Many Requests |
| Invalid API key | 401 Invalid API Key |
