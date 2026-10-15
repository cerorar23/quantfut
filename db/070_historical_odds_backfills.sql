-- Historical price provenance: effective price time is separate from reception.
-- Executed within the import transaction; existing immutable tables are untouched.
CREATE TABLE IF NOT EXISTS historical_odds_backfills (
    provider TEXT NOT NULL,
    source_match_id TEXT NOT NULL,
    raw_source_sha256 TEXT NOT NULL CHECK (raw_source_sha256 ~ '^[0-9a-f]{64}$'),
    match_id TEXT NOT NULL REFERENCES matches(match_id),
    league_id TEXT NOT NULL REFERENCES leagues(league_id),
    received_at TIMESTAMPTZ NOT NULL,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_1x2_gzip BYTEA NOT NULL,
    raw_1x2_sha256 TEXT NOT NULL CHECK (raw_1x2_sha256 ~ '^[0-9a-f]{64}$'),
    source_metadata JSONB NOT NULL,
    normalized JSONB NOT NULL,
    disposition TEXT NOT NULL CHECK (disposition IN ('close_inserted', 'reference_only', 'existing_close')),
    snapshot_ids BIGINT[] NOT NULL,
    PRIMARY KEY (provider, source_match_id, raw_source_sha256)
);
CREATE INDEX IF NOT EXISTS idx_historical_odds_backfill_match
    ON historical_odds_backfills(match_id);
CREATE OR REPLACE TRIGGER trg_historical_odds_backfill_immutable
    BEFORE UPDATE OR DELETE ON historical_odds_backfills
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();
COMMENT ON TABLE historical_odds_backfills IS
    'Historical reconstructed odds and reception evidence; reference_only never feeds closing prices.';
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='qf_readonly') THEN
        GRANT SELECT ON historical_odds_backfills TO qf_readonly;
    END IF;
END $$;
