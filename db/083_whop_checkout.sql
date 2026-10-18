-- Cobro web con Whop (2026-10-18). Spec: docs/superpowers/specs/2026-10-18-whop-checkout-meta-design.md.
-- Aditiva: no toca los triggers de subscriptions (db/043, solo se revoca).

ALTER TABLE plans ADD COLUMN IF NOT EXISTS whop_plan_id TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS plans_whop_plan_id ON plans (whop_plan_id) WHERE whop_plan_id IS NOT NULL;

-- Un intento de checkout = una configuración de Whop (ch_). Guarda lo que el navegador aportó para
-- que el Purchase de servidor lleve fbp/fbc/IP/UA del comprador (EMQ) y comparta event_id con el Pixel.
CREATE TABLE IF NOT EXISTS whop_checkouts (
    checkout_id TEXT PRIMARY KEY,
    account_id  BIGINT NOT NULL REFERENCES accounts(account_id),
    plan_code   TEXT NOT NULL REFERENCES plans(plan_code),
    event_id    TEXT NOT NULL,
    fbp         TEXT,
    fbc         TEXT,
    client_ip   TEXT,
    user_agent  TEXT,
    source_url  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS whop_checkouts_cuenta ON whop_checkouts (account_id, created_at DESC);

-- Entrega al menos una vez: el mismo webhook-id puede llegar repetido.
CREATE TABLE IF NOT EXISTS whop_webhooks (
    webhook_id  TEXT PRIMARY KEY,
    event_type  TEXT NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Un pago de Whop concede una sola vez.
CREATE TABLE IF NOT EXISTS whop_payments (
    payment_id      TEXT PRIMARY KEY,
    account_id      BIGINT NOT NULL REFERENCES accounts(account_id),
    plan_code       TEXT NOT NULL REFERENCES plans(plan_code),
    subscription_id BIGINT,
    checkout_id     TEXT,
    membership_id   TEXT,
    amount_cents    BIGINT,
    currency        TEXT,
    billing_reason  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS whop_payments_membresia ON whop_payments (membership_id);

-- Eventos de Meta que nacen en la web (action_source=website) llevan su contexto de navegador.
ALTER TABLE meta_events ADD COLUMN IF NOT EXISTS action_source TEXT NOT NULL DEFAULT 'app'
    CHECK (action_source IN ('app', 'website'));
ALTER TABLE meta_events ADD COLUMN IF NOT EXISTS web_context JSONB;
