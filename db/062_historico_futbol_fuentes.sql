-- Observaciones históricas con identidad por proveedor, fuera de capturas PIT.
BEGIN;
CREATE TABLE IF NOT EXISTS historical_football_matches (
    provider TEXT NOT NULL,
    source_match_id TEXT NOT NULL,
    league_id TEXT NOT NULL REFERENCES leagues(league_id),
    season TEXT NOT NULL,
    kickoff_utc TIMESTAMPTZ NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_sha256 TEXT NOT NULL CHECK (raw_sha256 ~ '^[0-9a-f]{64}$'),
    raw_payload_gzip BYTEA NOT NULL,
    raw_metadata JSONB NOT NULL,
    home_source_team_id TEXT NOT NULL,
    away_source_team_id TEXT NOT NULL,
    home_name TEXT NOT NULL,
    away_name TEXT NOT NULL,
    home_goals SMALLINT NOT NULL CHECK (home_goals >= 0),
    away_goals SMALLINT NOT NULL CHECK (away_goals >= 0),
    home_xg REAL CHECK (home_xg >= 0 AND home_xg < 'Infinity'::real),
    away_xg REAL CHECK (away_xg >= 0 AND away_xg < 'Infinity'::real),
    statistics JSONB NOT NULL,
    match_id TEXT REFERENCES matches(match_id),
    mapping_status TEXT NOT NULL CHECK (mapping_status IN ('matched','created','unresolved','conflict')),
    mapping_reason TEXT,
    PRIMARY KEY (provider,source_match_id),
    CHECK (home_source_team_id <> away_source_team_id),
    CHECK (captured_at >= kickoff_utc)
);
CREATE INDEX IF NOT EXISTS historical_football_match_link ON historical_football_matches(match_id);
CREATE UNIQUE INDEX IF NOT EXISTS historical_football_unique_provider_link
    ON historical_football_matches(provider,match_id) WHERE match_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS historical_football_league_date ON historical_football_matches(league_id,kickoff_utc);
CREATE TABLE IF NOT EXISTS historical_football_lineups (
    provider TEXT NOT NULL,
    source_match_id TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('home','away')),
    formation TEXT,
    complete BOOLEAN NOT NULL,
    starters JSONB NOT NULL,
    substitutes JSONB NOT NULL,
    PRIMARY KEY (provider,source_match_id,side),
    FOREIGN KEY (provider,source_match_id) REFERENCES historical_football_matches(provider,source_match_id)
);
CREATE TABLE IF NOT EXISTS historical_football_player_stats (
    provider TEXT NOT NULL,
    source_match_id TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('home','away')),
    source_player_id BIGINT NOT NULL,
    player_name TEXT NOT NULL,
    minutes REAL CHECK (minutes >= 0 AND minutes < 'Infinity'::real),
    starter BOOLEAN,
    statistics JSONB NOT NULL,
    PRIMARY KEY (provider,source_match_id,source_player_id),
    FOREIGN KEY (provider,source_match_id) REFERENCES historical_football_matches(provider,source_match_id)
);
CREATE TABLE IF NOT EXISTS historical_football_absences (
    provider TEXT NOT NULL,
    source_match_id TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('home','away')),
    source_player_id BIGINT NOT NULL,
    player_name TEXT NOT NULL,
    availability JSONB NOT NULL,
    PRIMARY KEY (provider,source_match_id,side,source_player_id),
    FOREIGN KEY (provider,source_match_id) REFERENCES historical_football_matches(provider,source_match_id)
);
COMMENT ON TABLE historical_football_matches IS
 'Originales históricos congelados, recepción real y vínculo canónico revisado; no son predicciones ni cuotas.';
COMMENT ON TABLE historical_football_lineups IS
 'XI histórico con IDs del proveedor. Nunca se inserta como XI capturado antes del partido.';
COMMENT ON TABLE historical_football_player_stats IS
 'IDs por proveedor, sin mezclarlos con player_id API-Football; ausencia de métrica no se convierte en cero.';
COMMENT ON TABLE historical_football_absences IS
 'Bajas declaradas al capturar el histórico; no acredita exhaustividad ni disponibilidad previa al partido.';
DO $$ BEGIN
 IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='qf_readonly') THEN
  GRANT SELECT ON historical_football_matches,historical_football_lineups,
    historical_football_player_stats,historical_football_absences TO qf_readonly;
 END IF;
END $$;
COMMIT;
