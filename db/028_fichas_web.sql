-- ============================================================================
-- 028 - Datos para las fichas de partido de la web (estilo webs de estadísticas)
--
-- Contenido, no criterio: ningún pick sale de aquí.
--
-- 1. `matches.stats`: TODAS las estadísticas del partido (posesión, faltas,
--    tarjetas, fueras de juego, paradas, pases, xG del proveedor…). La
--    respuesta de `/fixtures/statistics` ya la pedía `results.py` al cerrar
--    cada partido y solo guardaba tiros y córners: guardarla entera cuesta 0
--    peticiones más. Solo se rellena desde hoy (partidos cerrados por
--    API-Football).
-- 2. `standings`: clasificación por liga, una petición a `/standings` por liga
--    y día (`ingest/standings.py`). Es una FOTO que se reemplaza, no un
--    histórico: no lleva trigger de inmutabilidad.
-- 3. Índices por equipo: la forma y el cara a cara buscan "los últimos
--    partidos de este equipo" entre 51.000 partidos.
-- ============================================================================
BEGIN;

ALTER TABLE matches ADD COLUMN IF NOT EXISTS stats JSONB;
COMMENT ON COLUMN matches.stats IS
  'Estadísticas completas del partido {home:{...}, away:{...}} de '
  'API-Football /fixtures/statistics, normalizadas por ingest/estadisticas.py.';

CREATE INDEX IF NOT EXISTS idx_matches_home_ko ON matches (home_team_id, kickoff_utc DESC);
CREATE INDEX IF NOT EXISTS idx_matches_away_ko ON matches (away_team_id, kickoff_utc DESC);

CREATE TABLE IF NOT EXISTS standings (
    league_id      TEXT NOT NULL REFERENCES leagues(league_id),
    season         TEXT NOT NULL,
    grupo          TEXT NOT NULL DEFAULT '',   -- conferencias de la MLS, fases
    team_id        BIGINT NOT NULL REFERENCES teams(team_id),
    posicion       SMALLINT NOT NULL,
    puntos         SMALLINT NOT NULL,
    jugados        SMALLINT NOT NULL,
    ganados        SMALLINT NOT NULL,
    empatados      SMALLINT NOT NULL,
    perdidos       SMALLINT NOT NULL,
    goles_favor    SMALLINT NOT NULL,
    goles_contra   SMALLINT NOT NULL,
    forma          TEXT,                       -- 'WWDLW' del proveedor
    descripcion    TEXT,                       -- 'Promotion - Champions League'...
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (league_id, grupo, team_id)
);

-- Grafana (rol de solo lectura) ve también la tabla nueva.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qf_readonly') THEN
    GRANT SELECT ON standings TO qf_readonly;
  END IF;
END $$;

COMMIT;
