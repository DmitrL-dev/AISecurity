/**
 * Tenant API Keys Schema
 *
 * API keys scoped to tenants for external integration
 */

import {
  pgTable,
  uuid,
  varchar,
  jsonb,
  integer,
  boolean,
  timestamp,
  index,
} from "drizzle-orm/pg-core";
import { relations } from "drizzle-orm";
import { tenants } from "./tenants";

/**
 * API keys for external access
 */
export const tenantApiKeys = pgTable(
  "tenant_api_keys",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    tenantId: uuid("tenant_id")
      .references(() => tenants.id)
      .notNull(),
    name: varchar("name", { length: 100 }).notNull(),

    // Key storage (only hash stored, prefix for display)
    keyHash: varchar("key_hash", { length: 64 }).notNull(),
    keyPrefix: varchar("key_prefix", { length: 12 }).notNull(), // sk_live_xxxx

    // Permissions
    scopes: jsonb("scopes").default(["analyze"]).notNull(),
    rateLimit: integer("rate_limit").default(1000).notNull(), // per hour

    // Status
    isActive: boolean("is_active").default(true).notNull(),
    lastUsedAt: timestamp("last_used_at", { withTimezone: true }),
    expiresAt: timestamp("expires_at", { withTimezone: true }),

    // Audit
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
    createdBy: uuid("created_by"),
    revokedAt: timestamp("revoked_at", { withTimezone: true }),
    revokedBy: uuid("revoked_by"),
  },
  (table) => [
    index("api_keys_tenant_idx").on(table.tenantId),
    index("api_keys_prefix_idx").on(table.keyPrefix),
  ]
);

// Relations
export const tenantApiKeysRelations = relations(tenantApiKeys, ({ one }) => ({
  tenant: one(tenants, {
    fields: [tenantApiKeys.tenantId],
    references: [tenants.id],
  }),
}));

// Types
export type TenantApiKey = typeof tenantApiKeys.$inferSelect;
export type NewTenantApiKey = typeof tenantApiKeys.$inferInsert;
