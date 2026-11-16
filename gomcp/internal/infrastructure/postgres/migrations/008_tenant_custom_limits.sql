-- +goose Up
-- Nullable means inherit the existing plan. Existing rows keep their semantics;
-- explicit zero and -1 remain distinguishable from an absent override.
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS custom_max_events INTEGER;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS custom_max_scans INTEGER;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS custom_max_users INTEGER;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS custom_max_sensors INTEGER;

-- +goose Down
-- Older application versions ignore these fields; preserve operator settings.
SELECT 1;
