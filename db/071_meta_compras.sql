-- Suscripciones de Google Play / App Store y eventos para Meta (2026-10-15).
-- Spec: docs/superpowers/specs/2026-10-15-meta-compras-design.md. Aditiva: no toca
-- los triggers de subscriptions (db/043), que solo admite revocar.

ALTER TABLE plans ADD COLUMN IF NOT EXISTS play_product_id   TEXT;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS play_base_plan_id TEXT;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS apple_product_id  TEXT;
UPDATE plans SET play_product_id = 'quantfut_plus', play_base_plan_id = 'plus-1m',
                 apple_product_id = 'quantfut_plus_1m' WHERE plan_code = 'plus_1m';
UPDATE plans SET play_product_id = 'quantfut_plus', play_base_plan_id = 'plus-3m',
                 apple_product_id = 'quantfut_plus_3m' WHERE plan_code = 'plus_3m';
UPDATE plans SET play_product_id = 'quantfut_plus', play_base_plan_id = 'plus-6m',
                 apple_product_id = 'quantfut_plus_6m' WHERE plan_code = 'plus_6m';
CREATE UNIQUE INDEX IF NOT EXISTS plans_play_ids ON plans (play_product_id, play_base_plan_id)
    WHERE play_product_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS plans_apple_id ON plans (apple_product_id)
    WHERE apple_product_id IS NOT NULL;

-- UUID opaco que la app pasa como obfuscatedAccountId (Play) y appAccountToken (StoreKit 2).
-- Liga cada compra a una cuenta sin dar a la tienda datos personales.
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS store_account_token UUID NOT NULL DEFAULT gen_random_uuid();
CREATE UNIQUE INDEX IF NOT EXISTS accounts_store_account_token ON accounts (store_account_token);

-- NULL = la persona nunca eligió = activo (decisión del titular, 2026-10-15).
ALTER TABLE firebase_preferences ADD COLUMN IF NOT EXISTS ads_measurement BOOLEAN;

CREATE TABLE IF NOT EXISTS store_transactions (
    store            TEXT NOT NULL CHECK (store IN ('google_play', 'app_store')),
    order_id         TEXT NOT NULL,              -- orderId de Play / transactionId de Apple
    original_id      TEXT NOT NULL,              -- purchaseToken / originalTransactionId
    account_id       BIGINT NOT NULL REFERENCES accounts(account_id),
    plan_code        TEXT NOT NULL REFERENCES plans(plan_code),
    product_id       TEXT NOT NULL,
    base_plan_id     TEXT,
    period_start     TIMESTAMPTZ NOT NULL,
    period_end       TIMESTAMPTZ NOT NULL,
    price_micros     BIGINT CHECK (price_micros IS NULL OR price_micros >= 0),
    currency         TEXT CHECK (currency IS NULL OR currency ~ '^[A-Z]{3}$'),
    region_code      TEXT,
    environment      TEXT NOT NULL CHECK (environment IN ('production', 'sandbox')),
    subscription_id  BIGINT REFERENCES subscriptions(subscription_id),
    verified_payload JSONB NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (store, order_id),
    CHECK (period_end > period_start)
);
CREATE INDEX IF NOT EXISTS store_transactions_original ON store_transactions (store, original_id, period_end);
CREATE INDEX IF NOT EXISTS store_transactions_account ON store_transactions (account_id, created_at);

CREATE OR REPLACE FUNCTION store_transactions_inmutable() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'REGISTRO INMUTABLE: store_transactions no admite %', TG_OP;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS store_transactions_inmutable ON store_transactions;
CREATE TRIGGER store_transactions_inmutable BEFORE UPDATE OR DELETE ON store_transactions
    FOR EACH ROW EXECUTE FUNCTION store_transactions_inmutable();

-- Cola de Conversions API. event_id determinista (reg:/sub:/pur:/spend:) = idempotencia.
CREATE TABLE IF NOT EXISTS meta_events (
    event_id    TEXT PRIMARY KEY,
    account_id  BIGINT NOT NULL REFERENCES accounts(account_id),
    event_name  TEXT NOT NULL,
    event_time  TIMESTAMPTZ NOT NULL DEFAULT now(),
    custom_data JSONB NOT NULL DEFAULT '{}',
    status      TEXT NOT NULL DEFAULT 'pendiente'
                CHECK (status IN ('pendiente', 'enviado', 'omitido', 'fallido')),
    attempts    INTEGER NOT NULL DEFAULT 0,
    last_error  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    sent_at     TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS meta_events_pendientes ON meta_events (created_at) WHERE status = 'pendiente';

-- Datos operativos del dispositivo para user_data/app_data de CAPI. Entra en la limpieza
-- programada de datos operativos (docs/legal/OPERACION_PRIVACIDAD.md).
CREATE TABLE IF NOT EXISTS meta_identities (
    account_id  BIGINT NOT NULL REFERENCES accounts(account_id),
    anon_id     TEXT NOT NULL,
    platform    TEXT NOT NULL CHECK (platform IN ('android', 'ios')),
    madid       TEXT,
    advertiser_tracking_enabled BOOLEAN NOT NULL,
    extinfo     JSONB NOT NULL,
    client_ip   TEXT,
    user_agent  TEXT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (account_id, anon_id)
);
CREATE INDEX IF NOT EXISTS meta_identities_reciente ON meta_identities (account_id, updated_at DESC);
