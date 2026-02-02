/**
 * Usage Metrics Schema
 *
 * Tracks tenant usage for billing and rate limiting
 */

import {
  pgTable,
  uuid,
  date,
  integer,
  timestamp,
  index,
} from "drizzle-orm/pg-core";
import { relations } from "drizzle-orm";
import { tenants } from "./tenants";

/**
 * Daily usage metrics per tenant
 */
export const usageMetrics = pgTable(
  "usage_metrics",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    tenantId: uuid("tenant_id")
      .references(() => tenants.id)
      .notNull(),
    date: date("date").notNull(),

    // Counters
    apiCalls: integer("api_calls").default(0).notNull(),
    analyses: integer("analyses").default(0).notNull(),
    blockedThreats: integer("blocked_threats").default(0).notNull(),

    // Timestamps
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
  },
  (table) => [
    index("usage_tenant_date_idx").on(table.tenantId, table.date),
  ]
);

// Relations
export const usageMetricsRelations = relations(usageMetrics, ({ one }) => ({
  tenant: one(tenants, {
    fields: [usageMetrics.tenantId],
    references: [tenants.id],
  }),
}));

// Types
export type UsageMetric = typeof usageMetrics.$inferSelect;
export type NewUsageMetric = typeof usageMetrics.$inferInsert;
