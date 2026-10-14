-- PitchAPI como verificador y respaldo de API-Football (decisión del usuario,
-- 2026-10-14). Resultados: solo avisos de discrepancia. xG: relleno de respaldo
-- sobre partidos sin xG, con fecha real de recepción. Nunca sobrescribe.
BEGIN;

-- Un único registro. La clave se guarda CIFRADA (AES-256-GCM, comercial/cifrado.py)
-- y solo se escribe desde /control/respaldo: nunca se devuelve. key_hint son los
-- últimos 4 caracteres, para reconocerla. PITCHAPI_KEY del entorno sirve de respaldo.
CREATE TABLE IF NOT EXISTS pitchapi_settings (
    id             SMALLINT PRIMARY KEY CHECK (id = 1),
    enabled        BOOLEAN NOT NULL DEFAULT FALSE,
    key_enc        TEXT NOT NULL DEFAULT '',
    key_hint       TEXT NOT NULL DEFAULT '',
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_run_at    TIMESTAMPTZ,
    last_ok        BOOLEAN,
    last_detail    JSONB NOT NULL DEFAULT '{}'::jsonb
);
INSERT INTO pitchapi_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

ALTER TABLE leagues ADD COLUMN IF NOT EXISTS pitchapi_id TEXT;
COMMENT ON COLUMN leagues.pitchapi_id IS
  'ID de liga en PitchAPI (GET /v1/leagues). NULL: la competición no se coteja.';

-- Equivalencia equipo PitchAPI -> club canónico. Nunca por nombre: nace de
-- partidos corroborados (misma fecha UTC y marcador, candidato único).
CREATE TABLE IF NOT EXISTS pitchapi_teams (
    pitch_team_id TEXT PRIMARY KEY,
    team_id       BIGINT NOT NULL REFERENCES teams(team_id),
    votes         INTEGER NOT NULL,
    evidence      JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS pitchapi_teams_team_uniq ON pitchapi_teams (team_id);

-- Votos acumulados de las pasadas diarias para equipos aún sin equivalencia.
CREATE TABLE IF NOT EXISTS pitchapi_team_votes (
    pitch_team_id TEXT NOT NULL,
    team_id       BIGINT NOT NULL REFERENCES teams(team_id),
    pitch_match_id TEXT NOT NULL,
    PRIMARY KEY (pitch_team_id, team_id, pitch_match_id)
);

-- Diferencias entre la base y PitchAPI. Se detectan, se avisan y alguien las
-- revisa; el sistema no las corrige solo.
CREATE TABLE IF NOT EXISTS pitchapi_discrepancies (
    id             BIGSERIAL PRIMARY KEY,
    detected_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    kind           TEXT NOT NULL CHECK (kind IN ('score','result_pending','missing_in_db')),
    match_id       TEXT,
    league_id      TEXT NOT NULL,
    pitch_match_id TEXT NOT NULL,
    detail         JSONB NOT NULL DEFAULT '{}'::jsonb,
    reviewed_at    TIMESTAMPTZ,
    reviewed_by    TEXT
);
-- Misma diferencia, una sola fila abierta: la pasada diaria no la duplica.
CREATE UNIQUE INDEX IF NOT EXISTS pitchapi_discrepancies_open
    ON pitchapi_discrepancies (kind, pitch_match_id) WHERE reviewed_at IS NULL;

-- Originales de las estadísticas usadas para el xG, con hash y recepción.
CREATE TABLE IF NOT EXISTS pitchapi_originals (
    pitch_match_id TEXT NOT NULL,
    sha256         TEXT NOT NULL,
    match_id       TEXT,
    received_at    TIMESTAMPTZ NOT NULL,
    payload_gzip   BYTEA NOT NULL,
    PRIMARY KEY (pitch_match_id, sha256)
);

-- Ligas del catálogo actual (GET /v1/leagues, 14-oct-2026).
UPDATE leagues SET pitchapi_id = v.pid FROM (VALUES
 ('gb.premier_league','l_4WFCIZ'),('gb.championship','l_4DWyTT'),
 ('es.laliga','l_0ErfuF'),('es.laliga2','l_3kyHLd'),
 ('it.serie_a','l_0ALvwF'),('it.serie_b','l_0jy5yE'),
 ('de.bundesliga','l_1Isor4'),('de.bundesliga2','l_3hvsne'),
 ('fr.ligue_1','l_3FJFUl'),('fr.ligue_2','l_0275VP'),
 ('nl.eredivisie','l_4H43wr'),('pt.primeira','l_4QexZg'),
 ('tr.super_lig','l_0S1uaf'),('ch.super_league','l_4d6Bwl'),
 ('dk.superliga','l_49Zmno'),('no.eliteserien','l_0uqFK8'),
 ('se.allsvenskan','l_1XsMdH'),('us.mls','l_0eg6C9'),
 ('mx.liga_mx','l_3v84VE'),('br.serie_a','l_1D8Xrl'),
 ('ar.primera','l_45VZuL'),('eu.ucl','l_0bfbkO'),('eu.uel','l_38d9HA')
) AS v(lid, pid) WHERE leagues.league_id = v.lid;

COMMIT;
