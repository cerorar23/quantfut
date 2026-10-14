-- ============================================================================
-- 067 - F0: lo archivado de FotMob pasa a tablas consultables.
--       Spec docs/superpowers/specs/2026-10-14-senales-motor-principal-design.md
--
-- estadios: sede real con coordenadas (el motor no las usa todavía; F6).
-- matches_enriquecimiento: de dónde y cuándo llegó cada campo rellenado.
-- xGOT no es PSxG: columnas propias, nunca se copia a home_psxg.
-- referee_fotmob: matches.referee conserva el formato de API-Football que lee
-- el motor de tarjetas; F5 unifica identidades.
-- ============================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS estadios (
    stadium_id    BIGSERIAL PRIMARY KEY,
    name          TEXT NOT NULL,
    city          TEXT,
    country       TEXT,
    lat           DOUBLE PRECISION,
    lon           DOUBLE PRECISION,
    capacity      INTEGER,
    surface       TEXT,
    source        TEXT NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL,
    CHECK (lat BETWEEN -90 AND 90),
    CHECK (lon BETWEEN -180 AND 180),
    CHECK ((lat IS NULL) = (lon IS NULL)),
    CHECK (capacity IS NULL OR capacity > 0)
);
CREATE UNIQUE INDEX IF NOT EXISTS estadios_uq ON estadios (name, city, country) NULLS NOT DISTINCT;

ALTER TABLE matches ADD COLUMN IF NOT EXISTS stadium_id BIGINT REFERENCES estadios(stadium_id);
ALTER TABLE matches ADD COLUMN IF NOT EXISTS home_xgot REAL;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS away_xgot REAL;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS referee_fotmob TEXT;
CREATE INDEX IF NOT EXISTS idx_matches_stadium ON matches(stadium_id) WHERE stadium_id IS NOT NULL;

COMMENT ON COLUMN matches.home_xgot IS
    'xG de los remates a puerta (xGOT) del proveedor. NO equivale a home_psxg: otra definición y escala.';
COMMENT ON COLUMN matches.referee_fotmob IS
    'Árbitro tal como lo nombra FotMob. matches.referee conserva el formato de API-Football.';

CREATE TABLE IF NOT EXISTS matches_enriquecimiento (
    match_id        TEXT NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    campo           TEXT NOT NULL,
    provider        TEXT NOT NULL,
    source_match_id TEXT NOT NULL,
    captured_at     TIMESTAMPTZ NOT NULL,
    imported_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (match_id, campo)
);
COMMENT ON TABLE matches_enriquecimiento IS
    'Procedencia de cada campo de matches rellenado desde el archivo. captured_at = recepción real del original.';

DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qf_readonly') THEN
    GRANT SELECT ON estadios, matches_enriquecimiento TO qf_readonly;
  END IF;
END $$;

COMMIT;
