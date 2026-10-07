-- ============================================================================
-- 043 - Fase comercial: cuentas, planes, suscripciones y sesiones
-- (decisión del usuario, 2026-10-07). Las consume `src/qf/api/cuentas.py`
-- (web y app Flutter) y el panel `/control`.
--
-- `subscribers` de 001 no se reutiliza: nació para Telegram y no tiene
-- contraseña ni historial. Queda sin consumidores, como ya estaba.
--
-- Una suscripción concedida o pagada es un registro económico: no se borra
-- ni se edita. Lo único permitido es revocarla UNA vez, dejando quién y por
-- qué. El historial del panel (`admin_audit`) es inmutable, como `picks`.
-- ============================================================================
BEGIN;

CREATE EXTENSION IF NOT EXISTS citext;

CREATE TABLE IF NOT EXISTS accounts (
    account_id          BIGSERIAL PRIMARY KEY,
    email               CITEXT NOT NULL UNIQUE,
    password_hash       TEXT NOT NULL,
    display_name        TEXT,
    status              TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'suspended')),
    email_verified_at   TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at       TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_accounts_created ON accounts(created_at);

-- duration_days NULL = acceso de por vida (Club). `active` decide qué se
-- ofrece a la venta; el panel puede conceder cualquier plan a mano.
CREATE TABLE IF NOT EXISTS plans (
    plan_code       TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    duration_days   INTEGER CHECK (duration_days IS NULL OR duration_days > 0),
    price_cents     INTEGER NOT NULL CHECK (price_cents >= 0),
    currency        TEXT NOT NULL DEFAULT 'USD' CHECK (currency ~ '^[A-Z]{3}$'),
    active          BOOLEAN NOT NULL DEFAULT false,
    sort_order      INTEGER NOT NULL DEFAULT 0
);

-- Importes de docs/modelo_paquetes_suscripciones_20261007.md: ilustrativos
-- hasta que el usuario fije tarifas. Club queda fuera de venta, como propone
-- ese documento.
INSERT INTO plans (plan_code, name, duration_days, price_cents, currency, active, sort_order) VALUES
    ('plus_1m', 'Plus · 1 mes',   30,   1499, 'USD', true,  10),
    ('plus_3m', 'Plus · 3 meses', 90,   3399, 'USD', true,  20),
    ('plus_6m', 'Plus · 6 meses', 180,  5399, 'USD', true,  30),
    ('club',    'Club QuantFut',  NULL, 17999, 'USD', false, 40)
ON CONFLICT (plan_code) DO NOTHING;

CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id BIGSERIAL PRIMARY KEY,
    account_id      BIGINT NOT NULL REFERENCES accounts(account_id),
    plan_code       TEXT NOT NULL REFERENCES plans(plan_code),
    starts_at       TIMESTAMPTZ NOT NULL,
    ends_at         TIMESTAMPTZ,                 -- NULL = de por vida
    source          TEXT NOT NULL CHECK (source IN ('manual', 'payment')),
    price_cents     INTEGER NOT NULL DEFAULT 0 CHECK (price_cents >= 0),
    currency        TEXT NOT NULL DEFAULT 'USD',
    note            TEXT,
    created_by      TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at      TIMESTAMPTZ,
    revoked_by      TEXT,
    revoke_reason   TEXT,
    CHECK (ends_at IS NULL OR ends_at > starts_at),
    CHECK ((revoked_at IS NULL) = (revoked_by IS NULL))
);
CREATE INDEX IF NOT EXISTS idx_subs_account ON subscriptions(account_id, ends_at);
CREATE INDEX IF NOT EXISTS idx_subs_created ON subscriptions(created_at);

CREATE OR REPLACE FUNCTION subscriptions_only_revoke() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'REGISTRO INMUTABLE: subscriptions no admite DELETE';
    END IF;
    IF OLD.revoked_at IS NOT NULL
       OR (to_jsonb(NEW) - 'revoked_at' - 'revoked_by' - 'revoke_reason')
          IS DISTINCT FROM (to_jsonb(OLD) - 'revoked_at' - 'revoked_by' - 'revoke_reason')
    THEN
        RAISE EXCEPTION 'REGISTRO INMUTABLE: una suscripción solo se revoca, una vez';
    END IF;
    RETURN NEW;
END; $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_subs_only_revoke ON subscriptions;
CREATE TRIGGER trg_subs_only_revoke BEFORE UPDATE OR DELETE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION subscriptions_only_revoke();

-- Una fila por dispositivo con sesión. El refresh se rota en cada uso; el
-- anterior pasa a `session_retired_tokens`, y si alguien lo presenta de
-- nuevo es que se copió: se revoca la sesión entera.
CREATE TABLE IF NOT EXISTS sessions (
    session_id      BIGSERIAL PRIMARY KEY,
    account_id      BIGINT NOT NULL REFERENCES accounts(account_id),
    refresh_hash    BYTEA NOT NULL UNIQUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked_at      TIMESTAMPTZ,
    revoke_reason   TEXT,
    user_agent      TEXT,
    ip              TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_account ON sessions(account_id);

CREATE TABLE IF NOT EXISTS session_retired_tokens (
    token_hash      BYTEA PRIMARY KEY,
    session_id      BIGINT NOT NULL REFERENCES sessions(session_id),
    retired_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS admin_audit (
    audit_id    BIGSERIAL PRIMARY KEY,
    at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor       TEXT NOT NULL,
    action      TEXT NOT NULL,
    account_id  BIGINT REFERENCES accounts(account_id),
    detail      JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_admin_audit_at ON admin_audit(at DESC);

DROP TRIGGER IF EXISTS trg_admin_audit_immutable ON admin_audit;
CREATE TRIGGER trg_admin_audit_immutable BEFORE UPDATE OR DELETE ON admin_audit
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();

-- Sin GRANT a qf_readonly: Grafana no necesita correos ni hashes.

COMMIT;
