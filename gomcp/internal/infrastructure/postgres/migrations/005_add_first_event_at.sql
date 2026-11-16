-- +goose Up
-- Add first_event_at to soc_incidents: the timestamp of the EARLIEST correlated
-- event, the honest anchor for MTTD (detect latency = created_at - first_event_at).
-- Nullable: pre-migration rows have no value and are skipped by MTTD aggregation
-- rather than counted as a false 0s detection (IMP6).

ALTER TABLE soc_incidents ADD COLUMN IF NOT EXISTS first_event_at TIMESTAMPTZ;

-- +goose Down
ALTER TABLE soc_incidents DROP COLUMN IF EXISTS first_event_at;
