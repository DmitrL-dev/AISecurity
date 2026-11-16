-- +goose Up
-- Add tenant_id to SOC tables for multi-tenant isolation.
-- Safe: DEFAULT '' fills existing rows without data loss.

ALTER TABLE soc_events ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT '';
ALTER TABLE soc_incidents ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT '';
ALTER TABLE soc_sensors ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT '';

-- Tenant isolation indexes
CREATE INDEX IF NOT EXISTS idx_soc_events_tenant ON soc_events(tenant_id);
CREATE INDEX IF NOT EXISTS idx_soc_incidents_tenant ON soc_incidents(tenant_id);
CREATE INDEX IF NOT EXISTS idx_soc_sensors_tenant ON soc_sensors(tenant_id);

-- Composite indexes for common tenant-scoped queries
CREATE INDEX IF NOT EXISTS idx_soc_events_tenant_ts ON soc_events(tenant_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_soc_events_tenant_cat ON soc_events(tenant_id, category);
CREATE INDEX IF NOT EXISTS idx_soc_incidents_tenant_status ON soc_incidents(tenant_id, status);

-- +goose Down
DROP INDEX IF EXISTS idx_soc_incidents_tenant_status;
DROP INDEX IF EXISTS idx_soc_events_tenant_cat;
DROP INDEX IF EXISTS idx_soc_events_tenant_ts;
DROP INDEX IF EXISTS idx_soc_sensors_tenant;
DROP INDEX IF EXISTS idx_soc_incidents_tenant;
DROP INDEX IF EXISTS idx_soc_events_tenant;

ALTER TABLE soc_sensors DROP COLUMN IF EXISTS tenant_id;
ALTER TABLE soc_incidents DROP COLUMN IF EXISTS tenant_id;
ALTER TABLE soc_events DROP COLUMN IF EXISTS tenant_id;
