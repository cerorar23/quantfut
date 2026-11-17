-- Pasarelas de pago configurables desde /control (Whop: producción y sandbox).
-- Las claves se guardan CIFRADAS (AES-GCM, comercial/cifrado.py); la clave maestra no está en la base.
-- El sandbox solo lo ven las cuentas de `pasarela_cuentas_prueba`: el resto siempre paga en producción.
CREATE TABLE IF NOT EXISTS pasarela_config (
    proveedor          TEXT        NOT NULL,
    modo               TEXT        NOT NULL CHECK (modo IN ('live', 'sandbox')),
    api_key_enc        TEXT,
    webhook_secret_enc TEXT,
    account_id         TEXT,
    actualizado_por    TEXT        NOT NULL DEFAULT '',
    actualizado_en     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (proveedor, modo)
);

CREATE TABLE IF NOT EXISTS pasarela_cuentas_prueba (
    account_id   BIGINT      PRIMARY KEY REFERENCES accounts(account_id) ON DELETE CASCADE,
    agregada_por TEXT        NOT NULL DEFAULT '',
    creada_en    TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE plans ADD COLUMN IF NOT EXISTS whop_plan_id_sandbox TEXT;
ALTER TABLE whop_checkouts ADD COLUMN IF NOT EXISTS modo TEXT NOT NULL DEFAULT 'live'
    CHECK (modo IN ('live', 'sandbox'));
ALTER TABLE whop_payments ADD COLUMN IF NOT EXISTS modo TEXT NOT NULL DEFAULT 'live'
    CHECK (modo IN ('live', 'sandbox'));
