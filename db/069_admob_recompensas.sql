-- Anuncios con recompensa de AdMob (2026-10-14). Configuración editable desde
-- /control/anuncios y tablas de tickets y eventos. Las monedas se acreditan SOLO
-- por el callback firmado de Google (SSV); ver src/qf/api/anuncios.py.
-- Apagado y en modo prueba por defecto: nada se activa hasta configurarlo.
-- reward_ad_events es inmutable (deny_mutation, db/043): un evento no se reescribe.
BEGIN;
ALTER TABLE reward_settings
 ADD COLUMN IF NOT EXISTS ads_enabled BOOLEAN NOT NULL DEFAULT FALSE,
 ADD COLUMN IF NOT EXISTS ad_coins INTEGER NOT NULL DEFAULT 10 CHECK(ad_coins BETWEEN 1 AND 1000000),
 ADD COLUMN IF NOT EXISTS ad_daily_cap INTEGER NOT NULL DEFAULT 5 CHECK(ad_daily_cap BETWEEN 1 AND 50),
 ADD COLUMN IF NOT EXISTS ad_cooldown_seconds INTEGER NOT NULL DEFAULT 180 CHECK(ad_cooldown_seconds BETWEEN 0 AND 3600),
 ADD COLUMN IF NOT EXISTS ad_unit_android TEXT NOT NULL DEFAULT '' CHECK(ad_unit_android='' OR ad_unit_android ~ '^ca-app-pub-[0-9]{16}/[0-9]{10}$'),
 ADD COLUMN IF NOT EXISTS ad_unit_ios TEXT NOT NULL DEFAULT '' CHECK(ad_unit_ios='' OR ad_unit_ios ~ '^ca-app-pub-[0-9]{16}/[0-9]{10}$'),
 ADD COLUMN IF NOT EXISTS ad_test_mode BOOLEAN NOT NULL DEFAULT TRUE,
 ADD COLUMN IF NOT EXISTS admob_publisher_id TEXT NOT NULL DEFAULT '' CHECK(admob_publisher_id='' OR admob_publisher_id ~ '^pub-[0-9]{16}$');

CREATE TABLE IF NOT EXISTS reward_ad_tickets (
 nonce TEXT PRIMARY KEY, account_id BIGINT NOT NULL REFERENCES accounts(account_id),
 day DATE NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 expires_at TIMESTAMPTZ NOT NULL, used_at TIMESTAMPTZ, cancelled_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS reward_ad_tickets_open ON reward_ad_tickets(account_id)
 WHERE used_at IS NULL AND cancelled_at IS NULL;

CREATE TABLE IF NOT EXISTS reward_ad_events (
 transaction_id TEXT PRIMARY KEY, account_id BIGINT NOT NULL REFERENCES accounts(account_id),
 nonce TEXT NOT NULL, ad_unit TEXT NOT NULL DEFAULT '', coins BIGINT NOT NULL CHECK(coins>=0),
 outcome TEXT NOT NULL CHECK(outcome IN ('credited','rejected_cap','rejected_ticket','rejected_unit','rejected_account')),
 day DATE NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS reward_ad_events_account_day ON reward_ad_events(account_id,day) WHERE outcome='credited';
DROP TRIGGER IF EXISTS trg_reward_ad_events_immutable ON reward_ad_events;
CREATE TRIGGER trg_reward_ad_events_immutable BEFORE UPDATE OR DELETE ON reward_ad_events
 FOR EACH ROW EXECUTE FUNCTION deny_mutation();
COMMIT;
