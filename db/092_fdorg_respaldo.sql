-- football-data.org (v4) como testigo independiente de calendario y resultados
-- (decisión del titular, 2026-11-01). Solo compara y avisa: nunca escribe en matches.
-- Diseño: docs/superpowers/specs/2026-11-01-football-data-org-respaldo-design.md
-- Número 092: el 089 ya lo ocupa otra migración de main. En producción se aplicó el 1-nov-2026 con el nombre 089_fdorg_respaldo.sql (mismo contenido; todo es IF NOT EXISTS, reaplicar no cambia nada).
BEGIN;

-- Un único registro. La clave sale del entorno (FOOTBALL_DATA_ORG_KEY), no de la base.
CREATE TABLE IF NOT EXISTS fdorg_settings (
    id           SMALLINT PRIMARY KEY CHECK (id = 1),
    enabled      BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_run_at  TIMESTAMPTZ,
    last_ok      BOOLEAN,
    last_detail  JSONB NOT NULL DEFAULT '{}'::jsonb
);
INSERT INTO fdorg_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

-- No reutiliza fd_code: ese es de football-data.co.uk (CSV).
ALTER TABLE leagues ADD COLUMN IF NOT EXISTS fdorg_code TEXT;
COMMENT ON COLUMN leagues.fdorg_code IS
  'Código de competición en football-data.org v4. NULL: no se coteja.';

UPDATE leagues SET fdorg_code = v.code FROM (VALUES
 ('gb.premier_league','PL'),('gb.championship','ELC'),('es.laliga','PD'),
 ('it.serie_a','SA'),('de.bundesliga','BL1'),('fr.ligue_1','FL1'),
 ('nl.eredivisie','DED'),('pt.primeira','PPL'),('br.serie_a','BSA'),
 ('eu.ucl','CL')
) AS v(lid, code) WHERE leagues.league_id = v.lid;

-- Equivalencia equipo football-data.org -> club canónico. Nunca por nombre: nace de
-- partidos corroborados (misma fecha UTC y marcador, candidato único).
CREATE TABLE IF NOT EXISTS fdorg_teams (
    fdorg_team_id TEXT PRIMARY KEY,
    team_id       BIGINT NOT NULL REFERENCES teams(team_id),
    votes         INTEGER NOT NULL,
    evidence      JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS fdorg_teams_team_uniq ON fdorg_teams (team_id);

CREATE TABLE IF NOT EXISTS fdorg_team_votes (
    fdorg_team_id  TEXT NOT NULL,
    team_id        BIGINT NOT NULL REFERENCES teams(team_id),
    fdorg_match_id TEXT NOT NULL,
    PRIMARY KEY (fdorg_team_id, team_id, fdorg_match_id)
);

-- Diferencias entre la base y football-data.org. Se detectan y se avisan; el sistema
-- no las corrige solo.
CREATE TABLE IF NOT EXISTS fdorg_discrepancies (
    id             BIGSERIAL PRIMARY KEY,
    detected_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    kind           TEXT NOT NULL CHECK (kind IN ('score','result_pending','missing_in_db','kickoff_shift')),
    match_id       TEXT,
    league_id      TEXT NOT NULL,
    fdorg_match_id TEXT NOT NULL,
    detail         JSONB NOT NULL DEFAULT '{}'::jsonb,
    reviewed_at    TIMESTAMPTZ,
    reviewed_by    TEXT
);
-- Misma diferencia, una sola fila abierta: la pasada diaria no la duplica.
CREATE UNIQUE INDEX IF NOT EXISTS fdorg_discrepancies_open
    ON fdorg_discrepancies (kind, fdorg_match_id) WHERE reviewed_at IS NULL;

-- Respuestas originales con hash y recepción real (una por petición).
CREATE TABLE IF NOT EXISTS fdorg_originals (
    sha256       TEXT NOT NULL,
    window_from  DATE NOT NULL,
    window_to    DATE NOT NULL,
    received_at  TIMESTAMPTZ NOT NULL,
    payload_gzip BYTEA NOT NULL,
    PRIMARY KEY (sha256, window_from, window_to)
);

COMMIT;
