/**
 * Auth-related database schema
 * 
 * Tables for user preferences, API keys, and audit logging
 */

import {
  pgTable,
  uuid,
  varchar,
  text,
  timestamp,
  jsonb,
  boolean,
  inet,
} from "drizzle-orm/pg-core";
import { relations } from "drizzle-orm";

/**
 * User preferences - extends Keycloak user data
 */
export const userPreferences = pgTable("user_preferences", {
  id: uuid("id").primaryKey().defaultRandom(),
  keycloakId: varchar("keycloak_id", { length: 255 }).unique().notNull(),
  email: varchar("email", { length: 255 }).notNull(),
  displayName: varchar("display_name", { length: 255 }),
  timezone: varchar("timezone", { length: 50 }).default("UTC"),
  theme: varchar("theme", { length: 20 }).default("dark"),
  notificationSettings: jsonb("notification_settings").default({}),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
});

/**
 * API Keys for machine-to-machine authentication
 */
export const apiKeys = pgTable("api_keys", {
  id: uuid("id").primaryKey().defaultRandom(),
  userId: uuid("user_id").references(() => userPreferences.id),
  name: varchar("name", { length: 255 }).notNull(),
  keyHash: varchar("key_hash", { length: 255 }).notNull(), // bcrypt hash
  keyPrefix: varchar("key_prefix", { length: 8 }).notNull(), // First 8 chars for identification
  roles: text("roles").array().notNull().default([]),
  expiresAt: timestamp("expires_at", { withTimezone: true }),
  lastUsedAt: timestamp("last_used_at", { withTimezone: true }),
  isActive: boolean("is_active").default(true),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
});

/**
 * Auth audit log
 */
export const authAudit = pgTable("auth_audit", {
  id: uuid("id").primaryKey().defaultRandom(),
  eventType: varchar("event_type", { length: 50 }).notNull(), // login, logout, failed_login, token_refresh, access_denied
  userId: uuid("user_id"),
  keycloakId: varchar("keycloak_id", { length: 255 }),
  email: varchar("email", { length: 255 }),
  ipAddress: inet("ip_address"),
  userAgent: text("user_agent"),
  path: varchar("path", { length: 500 }),
  roles: text("roles").array(),
  success: boolean("success").default(true),
  errorMessage: text("error_message"),
  metadata: jsonb("metadata").default({}),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
});

// Relations
export const userPreferencesRelations = relations(userPreferences, ({ many }) => ({
  apiKeys: many(apiKeys),
}));

export const apiKeysRelations = relations(apiKeys, ({ one }) => ({
  user: one(userPreferences, {
    fields: [apiKeys.userId],
    references: [userPreferences.id],
  }),
}));

// Types
export type UserPreferences = typeof userPreferences.$inferSelect;
export type NewUserPreferences = typeof userPreferences.$inferInsert;
export type ApiKey = typeof apiKeys.$inferSelect;
export type NewApiKey = typeof apiKeys.$inferInsert;
export type AuthAuditLog = typeof authAudit.$inferSelect;
export type NewAuthAuditLog = typeof authAudit.$inferInsert;
