-- ============================================================================
-- 044 - Enlaces de un solo uso enviados por correo (Proton Mail, 2026-10-07):
-- verificación de correo y restablecimiento de contraseña.
--
-- Solo se guarda el sha256 del token: quien lea la base no puede usar los
-- enlaces pendientes. `used_at` se marca al consumirlo; un token usado o
-- caducado no vuelve a valer.
-- ============================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS email_tokens (
    token_hash  BYTEA PRIMARY KEY,
    account_id  BIGINT NOT NULL REFERENCES accounts(account_id),
    purpose     TEXT NOT NULL CHECK (purpose IN ('verify', 'reset')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ NOT NULL,
    used_at     TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_email_tokens_account ON email_tokens(account_id, purpose);

COMMIT;
