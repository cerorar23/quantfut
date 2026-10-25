-- Detalle de partidos terminados de SofaScore (recolector Apify, actor rl1987), cargado por
-- `qf.ingest.sofascore_partidos`. Sustituye al xG y las estadísticas de API-Football, que pasó al plan
-- gratuito el 22-oct-2026 (decisión del titular, 24-oct). `received_at` es la recepción real del
-- recolector: es la hora desde la que el xG puede usarse (point-in-time). Inmutable, como los originales.

CREATE TABLE IF NOT EXISTS sofascore_detalles (
    sofascore_id        BIGINT PRIMARY KEY,
    match_id            TEXT NOT NULL UNIQUE REFERENCES matches(match_id),
    league_id           TEXT NOT NULL,
    received_at         TIMESTAMPTZ NOT NULL,
    receipt_id          INTEGER NOT NULL,
    raw_sha256          TEXT NOT NULL CHECK (raw_sha256 ~ '^[0-9a-f]{64}$'),
    home_source_team_id TEXT NOT NULL,
    away_source_team_id TEXT NOT NULL,
    home_goals          SMALLINT NOT NULL CHECK (home_goals >= 0),
    away_goals          SMALLINT NOT NULL CHECK (away_goals >= 0),
    home_xg             REAL CHECK (home_xg >= 0),
    away_xg             REAL CHECK (away_xg >= 0),
    lineups             JSONB,
    statistics          JSONB NOT NULL,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_sofascore_detalles_immutable ON sofascore_detalles;
CREATE TRIGGER trg_sofascore_detalles_immutable
    BEFORE UPDATE OR DELETE ON sofascore_detalles
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();
