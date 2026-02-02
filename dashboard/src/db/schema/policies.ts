/**
 * Security Policies Schema
 * 
 * Tenant-specific security rules and blocklists
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
  pgEnum,
} from "drizzle-orm/pg-core";
import { relations } from "drizzle-orm";
import { tenants } from "./tenants";

// Policy action enum
export const policyActionEnum = pgEnum("policy_action", [
  "block",
  "warn",
  "log",
  "allow",
]);

// Policy target enum
export const policyTargetEnum = pgEnum("policy_target", [
  "prompt",
  "response",
  "both",
]);

/**
 * Security policies
 */
export const securityPolicies = pgTable("security_policies", {
  id: uuid("id").primaryKey().defaultRandom(),
  tenantId: uuid("tenant_id").references(() => tenants.id),
  
  name: varchar("name", { length: 255 }).notNull(),
  description: text("description"),
  
  // Rules
  target: policyTargetEnum("target").default("both"),
  action: policyActionEnum("action").default("block"),
  priority: integer("priority").default(100), // Lower = higher priority
  
  // Conditions (JSON for flexibility)
  conditions: jsonb("conditions").default({}),
  /*
   * Example conditions:
   * {
   *   "engines": ["injection", "jailbreak"],
   *   "risk_threshold": 0.7,
   *   "categories": ["harmful", "illegal"]
   * }
   */
  
  // Status
  isEnabled: boolean("is_enabled").default(true),
  
  // Timestamps
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
  createdBy: uuid("created_by"),
});

// Blocklist entry type enum
export const blocklistTypeEnum = pgEnum("blocklist_type", [
  "pattern",    // Regex pattern
  "keyword",    // Exact keyword
  "hash",       // Content hash
  "embedding",  // Semantic embedding
]);

/**
 * Blocklist entries
 */
export const blocklistEntries = pgTable("blocklist_entries", {
  id: uuid("id").primaryKey().defaultRandom(),
  tenantId: uuid("tenant_id").references(() => tenants.id),
  
  type: blocklistTypeEnum("type").default("keyword"),
  value: text("value").notNull(), // Pattern, keyword, or hash
  
  // Metadata
  category: varchar("category", { length: 100 }),
  reason: text("reason"),
  source: varchar("source", { length: 100 }), // manual, auto, imported
  
  // Status
  isActive: boolean("is_active").default(true),
  hitCount: integer("hit_count").default(0),
  lastHitAt: timestamp("last_hit_at", { withTimezone: true }),
  
  // Timestamps
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
  expiresAt: timestamp("expires_at", { withTimezone: true }),
  createdBy: uuid("created_by"),
});

// Relations
export const securityPoliciesRelations = relations(securityPolicies, ({ one }) => ({
  tenant: one(tenants, {
    fields: [securityPolicies.tenantId],
    references: [tenants.id],
  }),
}));

export const blocklistEntriesRelations = relations(blocklistEntries, ({ one }) => ({
  tenant: one(tenants, {
    fields: [blocklistEntries.tenantId],
    references: [tenants.id],
  }),
}));

// Types
export type SecurityPolicy = typeof securityPolicies.$inferSelect;
export type NewSecurityPolicy = typeof securityPolicies.$inferInsert;
export type BlocklistEntry = typeof blocklistEntries.$inferSelect;
export type NewBlocklistEntry = typeof blocklistEntries.$inferInsert;
