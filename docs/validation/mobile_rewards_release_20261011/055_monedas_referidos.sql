BEGIN;
CREATE TABLE IF NOT EXISTS reward_settings (
 id INTEGER PRIMARY KEY CHECK(id=1), enabled BOOLEAN NOT NULL DEFAULT TRUE,
 unlock_cost INTEGER NOT NULL DEFAULT 100 CHECK(unlock_cost BETWEEN 1 AND 1000000),
 attendance_enabled BOOLEAN NOT NULL DEFAULT TRUE,
 attendance_coins JSONB NOT NULL DEFAULT '[30,35,35,40,40,45,50]',
 referrals_enabled BOOLEAN NOT NULL DEFAULT TRUE,
 referrer_coins INTEGER NOT NULL DEFAULT 200 CHECK(referrer_coins BETWEEN 0 AND 1000000),
 invitee_coins INTEGER NOT NULL DEFAULT 100 CHECK(invitee_coins BETWEEN 0 AND 1000000),
 referral_min_coins INTEGER NOT NULL DEFAULT 100 CHECK(referral_min_coins BETWEEN 1 AND 1000000),
 message TEXT NOT NULL DEFAULT 'Recompensas temporalmente no disponibles',
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO reward_settings(id) VALUES(1) ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS reward_wallets (
 account_id BIGINT PRIMARY KEY REFERENCES accounts(account_id),
 uid TEXT NOT NULL UNIQUE, referral_code TEXT NOT NULL UNIQUE,
 balance BIGINT NOT NULL DEFAULT 0, streak INTEGER NOT NULL DEFAULT 0,
 last_attendance DATE, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS reward_ledger (
 ledger_id BIGSERIAL PRIMARY KEY, account_id BIGINT NOT NULL REFERENCES accounts(account_id),
 delta BIGINT NOT NULL, balance_after BIGINT NOT NULL,
 event_key TEXT NOT NULL UNIQUE, kind TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS reward_ledger_account ON reward_ledger(account_id,ledger_id DESC);
CREATE TABLE IF NOT EXISTS reward_unlocks (
 account_id BIGINT NOT NULL REFERENCES accounts(account_id),
 stream TEXT NOT NULL CHECK(stream IN ('alta_probabilidad','escalera')), pick_key TEXT NOT NULL,
 cost INTEGER NOT NULL CHECK(cost>0), created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 PRIMARY KEY(account_id,stream,pick_key)
);
CREATE TABLE IF NOT EXISTS reward_referrals (
 invitee_id BIGINT PRIMARY KEY REFERENCES accounts(account_id),
 referrer_id BIGINT NOT NULL REFERENCES accounts(account_id),
 CHECK(invitee_id<>referrer_id), qualified_at TIMESTAMPTZ,
 referrer_award INTEGER, invitee_award INTEGER, qualifying_event TEXT,
 qualifying_min_coins INTEGER,
 reversed_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS reward_providers (
 provider TEXT PRIMARY KEY, enabled BOOLEAN NOT NULL DEFAULT FALSE,
 public_id TEXT NOT NULL DEFAULT '', approved_ips TEXT NOT NULL DEFAULT '',
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO reward_providers(provider) VALUES ('revu'),('bitlabs'),('tapjoy'),('torox'),('ayet'),('adjoe') ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS reward_provider_events (
 provider TEXT NOT NULL REFERENCES reward_providers(provider), transaction_id TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('credit','reversal')),
 account_id BIGINT NOT NULL REFERENCES accounts(account_id), coins BIGINT NOT NULL CHECK(coins>=0),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), PRIMARY KEY(provider,transaction_id,state)
);
COMMIT;
