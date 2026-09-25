-- ============================================================================
-- 003: Soporte para API-Football (calendario, resultados, alineaciones)
--      y diagnóstico de emparejamiento de nombres entre fuentes.
-- ============================================================================

ALTER TABLE leagues
    ADD COLUMN IF NOT EXISTS api_football_id  INTEGER,
    ADD COLUMN IF NOT EXISTS fbref_league_id  TEXT,
    ADD COLUMN IF NOT EXISTS season_style     TEXT NOT NULL DEFAULT 'european';
    -- 'european' = 2025/26 cruzada | 'calendar' = temporada dentro de un año
    --  (Brasileirão, MLS) | 'apertura_clausura' = Liga MX, Argentina

COMMENT ON COLUMN leagues.season_style IS
  'Determina cómo se construye el parámetro season y cómo se agrupa el histórico';

-- IDs de API-Football. VERIFÍCALOS con scripts/verify_league_ids.py antes de
-- confiar en ellos: el proveedor los ha cambiado en el pasado.
UPDATE leagues SET api_football_id = 39,  fbref_league_id = 'ENG-Premier League'   WHERE league_id = 'gb.premier_league';
UPDATE leagues SET api_football_id = 140, fbref_league_id = 'ESP-La Liga'          WHERE league_id = 'es.laliga';
UPDATE leagues SET api_football_id = 135, fbref_league_id = 'ITA-Serie A'          WHERE league_id = 'it.serie_a';
UPDATE leagues SET api_football_id = 88,  fbref_league_id = 'NED-Eredivisie'       WHERE league_id = 'nl.eredivisie';
UPDATE leagues SET api_football_id = 262, season_style = 'apertura_clausura'       WHERE league_id = 'mx.liga_mx';
UPDATE leagues SET api_football_id = 71,  season_style = 'calendar'                WHERE league_id = 'br.serie_a';
UPDATE leagues SET api_football_id = 128, season_style = 'calendar'                WHERE league_id = 'ar.primera';

-- ---------------------------------------------------------------------------
-- Diagnóstico de nombres sin emparejar.
-- El fallo silencioso más caro de estos sistemas: el join no falla, solo
-- devuelve menos filas, y te enteras tres meses después.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS unresolved_names (
    id          BIGSERIAL PRIMARY KEY,
    raw_name    TEXT NOT NULL,
    source      TEXT NOT NULL,
    league_id   TEXT REFERENCES leagues(league_id),
    best_guess  TEXT,
    score       REAL,
    occurrences INTEGER NOT NULL DEFAULT 1,
    first_seen  TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen   TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved    BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (raw_name, source)
);
CREATE INDEX IF NOT EXISTS idx_unresolved_pending
    ON unresolved_names(league_id) WHERE NOT resolved;

-- Permitir alias sin team_id mientras están pendientes de resolver
ALTER TABLE team_aliases ALTER COLUMN team_id DROP NOT NULL;

-- ---------------------------------------------------------------------------
-- Alineaciones confirmadas (se rellena en fase 4, la tabla se crea ya)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS lineups (
    match_id        TEXT NOT NULL REFERENCES matches(match_id),
    side            TEXT NOT NULL,              -- 'home' | 'away'
    formation       TEXT,
    starters        JSONB NOT NULL,             -- [{player_id, name, pos, number}]
    captured_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    mins_to_kickoff INTEGER NOT NULL,
    PRIMARY KEY (match_id, side, captured_at)
);

-- ---------------------------------------------------------------------------
-- Registro de salud de la ingesta. Si una fuente deja de devolver datos,
-- esto lo hace visible en vez de dejarlo pasar.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS ingest_health (
    id           BIGSERIAL PRIMARY KEY,
    source       TEXT NOT NULL,
    ran_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    rows_written INTEGER NOT NULL,
    ok           BOOLEAN NOT NULL,
    detail       JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_health_source ON ingest_health(source, ran_at DESC);

CREATE OR REPLACE VIEW v_ingest_status AS
SELECT DISTINCT ON (source)
    source, ran_at, rows_written, ok,
    EXTRACT(EPOCH FROM (now() - ran_at)) / 3600 AS hours_since
FROM ingest_health
ORDER BY source, ran_at DESC;
