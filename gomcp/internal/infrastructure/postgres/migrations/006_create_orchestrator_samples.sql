-- +goose Up
-- Data-capture flywheel: one TRAINING ROW per scan — the per-engine confidence
-- features + the verdict + a slot for an analyst LABEL attached later. Exported
-- as a (features, label) table to retrain the learned verdict-combiner/router
-- from real production traffic.
--
-- PRIVACY: metadata only. prompt_hash is a one-way SHA-256 of the prompt; the raw
-- prompt is NEVER stored. tenant_id scopes every query (multi-tenant isolation).

CREATE TABLE orchestrator_samples (
    id              TEXT PRIMARY KEY,
    tenant_id       TEXT NOT NULL DEFAULT '',
    timestamp       TIMESTAMPTZ NOT NULL,
    prompt_hash     TEXT NOT NULL DEFAULT '',
    -- engine_vector: dense per-engine vector when available (see domain doc:
    -- empty today because the bridge only returns aggregate + sparse scores).
    engine_vector   JSONB NOT NULL DEFAULT '[]',
    -- engine_scores: SPARSE {engine: confidence} parsed from indicators.
    engine_scores   JSONB NOT NULL DEFAULT '{}',
    -- aggregate: the dense scalar features available today (risk, per-tier conf,
    -- engines_triggered, per-tier block flags).
    aggregate       JSONB NOT NULL DEFAULT '{}',
    vector_complete BOOLEAN NOT NULL DEFAULT FALSE,
    vector_schema   TEXT NOT NULL DEFAULT '',
    blocked         BOOLEAN NOT NULL DEFAULT FALSE,
    risk            DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    threat_type     TEXT NOT NULL DEFAULT '',
    model_version   TEXT NOT NULL DEFAULT '',
    label           TEXT NOT NULL DEFAULT '',
    label_source    TEXT NOT NULL DEFAULT '',
    labeled_at      TIMESTAMPTZ
);

CREATE INDEX idx_orch_samples_tenant       ON orchestrator_samples(tenant_id);
CREATE INDEX idx_orch_samples_ts           ON orchestrator_samples(timestamp);
-- Composite indexes for the label-attach join (tenant + time window) and the
-- tenant-scoped labeled export.
CREATE INDEX idx_orch_samples_tenant_ts    ON orchestrator_samples(tenant_id, timestamp);
CREATE INDEX idx_orch_samples_tenant_label ON orchestrator_samples(tenant_id, label);

-- +goose Down
DROP TABLE IF EXISTS orchestrator_samples;
