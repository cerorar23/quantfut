-- Firebase identifica; las cuentas, permisos y saldo siguen en Postgres.
BEGIN;
ALTER TABLE accounts ALTER COLUMN password_hash DROP NOT NULL;

CREATE TABLE IF NOT EXISTS firebase_identities (
    project_id TEXT NOT NULL,
    firebase_uid TEXT NOT NULL,
    account_id BIGINT NOT NULL REFERENCES accounts(account_id),
    provider TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (project_id, firebase_uid),
    UNIQUE (project_id, account_id)
);
CREATE TABLE IF NOT EXISTS account_consents (
    account_id BIGINT NOT NULL REFERENCES accounts(account_id),
    terms_version TEXT NOT NULL,
    privacy_version TEXT NOT NULL,
    accepted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (account_id, terms_version, privacy_version)
);
CREATE TABLE IF NOT EXISTS firebase_preferences (
    account_id BIGINT PRIMARY KEY REFERENCES accounts(account_id),
    language TEXT NOT NULL DEFAULT 'es' CHECK (language IN ('es','en','pt','fr','it','de')),
    analytics BOOLEAN NOT NULL DEFAULT false,
    diagnostics BOOLEAN NOT NULL DEFAULT false,
    push_enabled BOOLEAN NOT NULL DEFAULT false,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS push_devices (
    installation_id UUID PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts(account_id),
    token TEXT NOT NULL UNIQUE,
    platform TEXT NOT NULL CHECK (platform IN ('android','ios')),
    language TEXT NOT NULL CHECK (language IN ('es','en','pt','fr','it','de')),
    enabled BOOLEAN NOT NULL DEFAULT true,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_push_devices_account ON push_devices(account_id);
CREATE TABLE IF NOT EXISTS account_notifications (
    notification_id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts(account_id),
    event_key TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    match_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    read_at TIMESTAMPTZ,
    UNIQUE (account_id, event_key)
);
CREATE TABLE IF NOT EXISTS notification_outbox (
    outbox_id BIGSERIAL PRIMARY KEY,
    notification_id BIGINT NOT NULL REFERENCES account_notifications(notification_id),
    installation_id UUID NOT NULL REFERENCES push_devices(installation_id),
    account_id BIGINT NOT NULL REFERENCES accounts(account_id),
    attempts INTEGER NOT NULL DEFAULT 0,
    sent_at TIMESTAMPTZ,
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_error TEXT,
    UNIQUE (notification_id, installation_id)
);
COMMIT;
