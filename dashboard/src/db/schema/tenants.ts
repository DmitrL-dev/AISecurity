/**
 * Tenant Schema
 * 
 * Multi-tenant support for SENTINEL
 */

import {
  pgTable,
  uuid,
  varchar,
  text,
  timestamp,
  jsonb,
  boolean,
  pgEnum,
} from "drizzle-orm/pg-core";
import { relations } from "drizzle-orm";
import { userPreferences } from "./auth";

// Tenant plan enum
export const tenantPlanEnum = pgEnum("tenant_plan", [
  "community",  // Free tier
  "professional",
  "enterprise",
]);

/**
 * Tenants table
 */
export const tenants = pgTable("tenants", {
  id: uuid("id").primaryKey().defaultRandom(),
  name: varchar("name", { length: 255 }).notNull(),
  slug: varchar("slug", { length: 100 }).unique().notNull(),
  plan: tenantPlanEnum("plan").default("community"),
  
  // Settings
  settings: jsonb("settings").default({}),
  features: jsonb("features").default({}), // Feature flags per tenant
  
  // Limits
  maxUsers: varchar("max_users", { length: 10 }).default("10"),
  maxApiKeys: varchar("max_api_keys", { length: 10 }).default("5"),
  
  // Status
  isActive: boolean("is_active").default(true),
  suspendedAt: timestamp("suspended_at", { withTimezone: true }),
  suspendReason: text("suspend_reason"),
  
  // Timestamps
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
});

// Member role enum
export const memberRoleEnum = pgEnum("member_role", [
  "owner",
  "admin",
  "member",
  "viewer",
]);

/**
 * Tenant members (user <-> tenant mapping)
 */
export const tenantMembers = pgTable("tenant_members", {
  id: uuid("id").primaryKey().defaultRandom(),
  tenantId: uuid("tenant_id").references(() => tenants.id).notNull(),
  userId: uuid("user_id").references(() => userPreferences.id).notNull(),
  role: memberRoleEnum("role").default("member"),
  
  // Invitation
  invitedBy: uuid("invited_by"),
  invitedAt: timestamp("invited_at", { withTimezone: true }),
  acceptedAt: timestamp("accepted_at", { withTimezone: true }),
  
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
});

// Relations
export const tenantsRelations = relations(tenants, ({ many }) => ({
  members: many(tenantMembers),
}));

export const tenantMembersRelations = relations(tenantMembers, ({ one }) => ({
  tenant: one(tenants, {
    fields: [tenantMembers.tenantId],
    references: [tenants.id],
  }),
  user: one(userPreferences, {
    fields: [tenantMembers.userId],
    references: [userPreferences.id],
  }),
}));

// Types
export type Tenant = typeof tenants.$inferSelect;
export type NewTenant = typeof tenants.$inferInsert;
export type TenantMember = typeof tenantMembers.$inferSelect;
export type NewTenantMember = typeof tenantMembers.$inferInsert;
