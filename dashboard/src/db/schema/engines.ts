/**
 * Engine Configuration Schema
 * 
 * Per-tenant engine settings and execution logs
 */

import {
  pgTable,
  uuid,
  varchar,
  text,
  timestamp,
  jsonb,
  boolean,
  integer,
  real,
} from "drizzle-orm/pg-core";
import { relations } from "drizzle-orm";
import { tenants } from "./tenants";

/**
 * Engine configurations per tenant
 */
export const engineConfigs = pgTable("engine_configs", {
  id: uuid("id").primaryKey().defaultRandom(),
  tenantId: uuid("tenant_id").references(() => tenants.id),
  
  // Engine identification
  engineName: varchar("engine_name", { length: 100 }).notNull(),
  // e.g., "injection", "jailbreak", "pii", "toxicity", "qwen_guard"
  
  // Configuration
  isEnabled: boolean("is_enabled").default(true),
  threshold: real("threshold").default(0.7), // Detection threshold
  mode: varchar("mode", { length: 50 }).default("standard"),
  // e.g., "strict", "standard", "permissive"
  
  // Custom settings (JSON for flexibility)
  settings: jsonb("settings").default({}),
  /*
   * Example settings:
   * {
   *   "categories": ["explicit", "violence"],
   *   "languages": ["en", "ru"],
   *   "custom_patterns": [...]
   * }
   */
  
  // Timestamps
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
});

/**
 * Engine execution logs (for analytics)
 */
export const engineLogs = pgTable("engine_logs", {
  id: uuid("id").primaryKey().defaultRandom(),
  tenantId: uuid("tenant_id").references(() => tenants.id),
  
  // Execution details
  engineName: varchar("engine_name", { length: 100 }).notNull(),
  promptHash: varchar("prompt_hash", { length: 64 }), // SHA-256 for dedup
  
  // Results
  riskScore: real("risk_score"),
  isBlocked: boolean("is_blocked").default(false),
  categories: jsonb("categories").default([]), // Detected categories
  
  // Performance
  latencyMs: integer("latency_ms"),
  tokensAnalyzed: integer("tokens_analyzed"),
  
  // Metadata
  metadata: jsonb("metadata").default({}),
  
  // Timestamp
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
});

// Relations
export const engineConfigsRelations = relations(engineConfigs, ({ one }) => ({
  tenant: one(tenants, {
    fields: [engineConfigs.tenantId],
    references: [tenants.id],
  }),
}));

export const engineLogsRelations = relations(engineLogs, ({ one }) => ({
  tenant: one(tenants, {
    fields: [engineLogs.tenantId],
    references: [tenants.id],
  }),
}));

// Types
export type EngineConfig = typeof engineConfigs.$inferSelect;
export type NewEngineConfig = typeof engineConfigs.$inferInsert;
export type EngineLog = typeof engineLogs.$inferSelect;
export type NewEngineLog = typeof engineLogs.$inferInsert;
