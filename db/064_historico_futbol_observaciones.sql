-- Capturas adicionales: conservan el primer original y su recepción.
BEGIN;
CREATE TABLE IF NOT EXISTS historical_football_observations (
 provider TEXT NOT NULL,
 source_match_id TEXT NOT NULL,
 raw_sha256 TEXT NOT NULL CHECK(raw_sha256 ~ '^[0-9a-f]{64}$'),
 match_id TEXT NOT NULL REFERENCES matches(match_id),
 league_id TEXT NOT NULL REFERENCES leagues(league_id),
 captured_at TIMESTAMPTZ NOT NULL,
 imported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 raw_payload_gzip BYTEA NOT NULL,
 raw_metadata JSONB NOT NULL,
 normalized JSONB NOT NULL,
 PRIMARY KEY(provider,source_match_id,raw_sha256),
 FOREIGN KEY(provider,source_match_id)
  REFERENCES historical_football_matches(provider,source_match_id)
);
CREATE INDEX IF NOT EXISTS historical_football_observation_match
 ON historical_football_observations(match_id,captured_at);
DROP TRIGGER IF EXISTS trg_football_observation_immutable ON historical_football_observations;
CREATE TRIGGER trg_football_observation_immutable BEFORE UPDATE OR DELETE
 ON historical_football_observations FOR EACH ROW EXECUTE FUNCTION deny_mutation();
COMMENT ON TABLE historical_football_observations IS
 'Observaciones suplementarias inmutables, con recepción propia; no sobreescriben el primer original ni anticipan datos nuevos.';
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='qf_readonly') THEN
  GRANT SELECT ON historical_football_observations TO qf_readonly;
 END IF;
END $$;
COMMIT;
