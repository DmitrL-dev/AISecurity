-- +goose Up
-- SENTINEL SOC — PostgreSQL Schema
-- Tables: soc_events, soc_incidents, soc_sensors

CREATE TABLE soc_events (
    id            TEXT PRIMARY KEY,
    source        TEXT NOT NULL,
    sensor_id     TEXT NOT NULL DEFAULT '',
    severity      TEXT NOT NULL,
    category      TEXT NOT NULL,
    subcategory   TEXT NOT NULL DEFAULT '',
    confidence    DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    description   TEXT NOT NULL DEFAULT '',
    session_id    TEXT NOT NULL DEFAULT '',
    content_hash  TEXT NOT NULL DEFAULT '',
    decision_hash TEXT NOT NULL DEFAULT '',
    verdict       TEXT NOT NULL DEFAULT 'REVIEW',
    timestamp     TIMESTAMPTZ NOT NULL,
    metadata      JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE soc_incidents (
    id                    TEXT PRIMARY KEY,
    status                TEXT NOT NULL DEFAULT 'OPEN',
    severity              TEXT NOT NULL,
    title                 TEXT NOT NULL,
    description           TEXT NOT NULL DEFAULT '',
    event_ids             JSONB NOT NULL DEFAULT '[]',
    event_count           INTEGER NOT NULL DEFAULT 0,
    decision_chain_anchor TEXT NOT NULL DEFAULT '',
    chain_length          INTEGER NOT NULL DEFAULT 0,
    correlation_rule      TEXT NOT NULL DEFAULT '',
    kill_chain_phase      TEXT NOT NULL DEFAULT '',
    mitre_mapping         JSONB NOT NULL DEFAULT '[]',
    playbook_applied      TEXT NOT NULL DEFAULT '',
    created_at            TIMESTAMPTZ NOT NULL,
    updated_at            TIMESTAMPTZ NOT NULL,
    resolved_at           TIMESTAMPTZ
);

CREATE TABLE soc_sensors (
    sensor_id         TEXT PRIMARY KEY,
    sensor_type       TEXT NOT NULL,
    status            TEXT DEFAULT 'UNKNOWN',
    first_seen        TIMESTAMPTZ NOT NULL,
    last_seen         TIMESTAMPTZ NOT NULL,
    event_count       INTEGER DEFAULT 0,
    missed_heartbeats INTEGER DEFAULT 0,
    hostname          TEXT NOT NULL DEFAULT '',
    version           TEXT NOT NULL DEFAULT ''
);

-- Indexes
CREATE INDEX idx_soc_events_timestamp    ON soc_events(timestamp);
CREATE INDEX idx_soc_events_severity     ON soc_events(severity);
CREATE INDEX idx_soc_events_category     ON soc_events(category);
CREATE INDEX idx_soc_events_sensor       ON soc_events(sensor_id);
CREATE INDEX idx_soc_events_content_hash ON soc_events(content_hash);
CREATE INDEX idx_soc_incidents_status    ON soc_incidents(status);
CREATE INDEX idx_soc_sensors_status      ON soc_sensors(status);

-- +goose Down
DROP TABLE IF EXISTS soc_sensors;
DROP TABLE IF EXISTS soc_incidents;
DROP TABLE IF EXISTS soc_events;
