-- +goose Up
-- Add fields already represented by the public incident contract. Defaults
-- preserve existing incidents; no retained evidence is dropped or rewritten.
ALTER TABLE soc_incidents ADD COLUMN IF NOT EXISTS assigned_to TEXT NOT NULL DEFAULT '';
ALTER TABLE soc_incidents ADD COLUMN IF NOT EXISTS notes_json JSONB NOT NULL DEFAULT '[]';
ALTER TABLE soc_incidents ADD COLUMN IF NOT EXISTS timeline_json JSONB NOT NULL DEFAULT '[]';

-- +goose Down
-- Deliberate no-op: rollback of application code must not discard case evidence.
SELECT 1;
