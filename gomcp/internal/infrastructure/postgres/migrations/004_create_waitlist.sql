-- +goose Up
-- Pre-signup waitlist (deletable PII store — GDPR Art.17). Cleartext registration
-- interest lives here, NOT in the immutable decision audit chain (which keeps only
-- a salted hash that a signup occurred). Erasable per subject via email.

CREATE TABLE IF NOT EXISTS soc_waitlist (
    id         TEXT PRIMARY KEY,
    email      TEXT NOT NULL,
    company    TEXT NOT NULL DEFAULT '',
    use_case   TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_soc_waitlist_email ON soc_waitlist(email);

-- +goose Down
DROP INDEX IF EXISTS idx_soc_waitlist_email;
DROP TABLE IF EXISTS soc_waitlist;
