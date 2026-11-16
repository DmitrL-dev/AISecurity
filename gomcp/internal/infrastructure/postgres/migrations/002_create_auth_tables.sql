-- +goose Up
-- SENTINEL SOC — Auth & Multi-Tenancy (PostgreSQL)
-- Tables: users, api_keys, tenants

CREATE TABLE IF NOT EXISTS users (
    id           TEXT PRIMARY KEY,
    email        TEXT UNIQUE NOT NULL,
    name         TEXT NOT NULL DEFAULT '',
    password     TEXT NOT NULL,
    role         TEXT NOT NULL DEFAULT 'viewer',
    tenant_id    TEXT NOT NULL DEFAULT '',
    active       BOOLEAN NOT NULL DEFAULT true,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS api_keys (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    key_hash    TEXT UNIQUE NOT NULL,
    key_prefix  TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'viewer',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used   TIMESTAMPTZ,
    active      BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS tenants (
    id                 TEXT PRIMARY KEY,
    name               TEXT NOT NULL,
    slug               TEXT UNIQUE NOT NULL,
    plan_id            TEXT NOT NULL DEFAULT 'free',
    stripe_customer_id TEXT NOT NULL DEFAULT '',
    stripe_sub_id      TEXT NOT NULL DEFAULT '',
    owner_user_id      TEXT NOT NULL,
    active             BOOLEAN NOT NULL DEFAULT true,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    events_this_month  INTEGER NOT NULL DEFAULT 0,
    month_reset_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add assigned_to column to incidents (was missing in 001)
ALTER TABLE soc_incidents ADD COLUMN IF NOT EXISTS assigned_to TEXT NOT NULL DEFAULT '';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_tenants_slug ON tenants(slug);
CREATE INDEX IF NOT EXISTS idx_tenants_owner ON tenants(owner_user_id);

-- +goose Down
DROP TABLE IF EXISTS tenants;
DROP TABLE IF EXISTS api_keys;
DROP TABLE IF EXISTS users;
ALTER TABLE soc_incidents DROP COLUMN IF EXISTS assigned_to;
