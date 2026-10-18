-- 081: captura recurrente de FotMob (autorizada por el titular el 18-oct-2026).
--
-- Tres capturas con su hora real de recepción (point-in-time):
--   previo     instantáneas de un partido futuro en cuatro ventanas: alineación probable o confirmada, no disponibles
--              con su tipo, entrenadores, valor del once y PRONÓSTICO de clima. Es lo único anterior al saque.
--   posterior  la página del partido terminado; alimenta fotmob_partido / fotmob_jugador_partido / fotmob_baja (075).
--   referencia qué id de FotMob corresponde a cada partido nuestro.
-- El original comprimido de cada captura nueva se conserva en fotmob_original (procedencia y reprocesado).
-- Las capturas se detienen ante HTTP 401, 403 o 429 y no se reintentan durante 12 h (ver fotmob_captura_log).
BEGIN;

CREATE TABLE IF NOT EXISTS fotmob_equipo (
    fotmob_team_id BIGINT PRIMARY KEY,
    team_id        BIGINT NOT NULL REFERENCES teams(team_id),
    partidos       INTEGER NOT NULL,         -- partidos de liga del archivo que lo prueban
    creado_en      TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Solo identidades probadas con partidos de liga y un único equipo nuestro. Sin datos no inserta nada.
INSERT INTO fotmob_equipo (fotmob_team_id, team_id, partidos)
SELECT sid::bigint, min(team_id), count(*)
FROM (
    SELECT h.home_source_team_id AS sid, m.home_team_id AS team_id
    FROM historical_football_matches h JOIN matches m USING (match_id)
    WHERE h.provider = 'fotmob' AND h.mapping_status IN ('matched', 'created') AND m.league_id NOT LIKE 'eu.%'
    UNION ALL
    SELECT h.away_source_team_id, m.away_team_id
    FROM historical_football_matches h JOIN matches m USING (match_id)
    WHERE h.provider = 'fotmob' AND h.mapping_status IN ('matched', 'created') AND m.league_id NOT LIKE 'eu.%'
) x
WHERE sid IS NOT NULL
GROUP BY sid
HAVING count(DISTINCT team_id) = 1
ON CONFLICT (fotmob_team_id) DO NOTHING;

CREATE TABLE IF NOT EXISTS fotmob_referencia (
    match_id        TEXT PRIMARY KEY REFERENCES matches(match_id),
    fotmob_match_id TEXT NOT NULL UNIQUE,
    fuente          TEXT NOT NULL CHECK (fuente IN ('archivo', 'liga')),
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO fotmob_referencia (match_id, fotmob_match_id, fuente)
SELECT match_id, source_match_id, 'archivo' FROM historical_football_matches
WHERE provider = 'fotmob' AND match_id IS NOT NULL
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS fotmob_original (
    id              BIGSERIAL PRIMARY KEY,
    match_id        TEXT NOT NULL REFERENCES matches(match_id),
    fotmob_match_id TEXT NOT NULL,
    fase            TEXT NOT NULL CHECK (fase IN ('previo', 'posterior')),
    capturado_en    TIMESTAMPTZ NOT NULL DEFAULT now(),
    mins_to_kickoff REAL,
    raw_sha256      TEXT NOT NULL,
    payload_gz      BYTEA NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fotmob_original_partido ON fotmob_original (match_id, fase, capturado_en);

CREATE TABLE IF NOT EXISTS fotmob_previo (
    match_id        TEXT NOT NULL REFERENCES matches(match_id),
    capturado_en    TIMESTAMPTZ NOT NULL,
    mins_to_kickoff REAL NOT NULL,
    ventana         TEXT NOT NULL,           -- dia (~24 h), horas (~4 h), final (~70 min), cierre (~40 min)
    tipo_alineacion TEXT,                    -- predicted | confirmed, según FotMob
    formacion_local TEXT,
    formacion_visita TEXT,
    valor_xi_local  BIGINT,
    valor_xi_visita BIGINT,
    entrenador_local  TEXT,
    entrenador_visita TEXT,
    clima_temperatura_c REAL,
    clima_viento        REAL,
    clima_direccion     TEXT,
    clima_humedad       REAL,
    clima_precipitacion REAL,
    clima_prob_precipitacion REAL,
    clima_nubosidad     REAL,
    clima_descripcion   TEXT,
    clima_api           TEXT,                -- forecast | current | historical, según FotMob
    clima_actualizado   TIMESTAMPTZ,
    original_id     BIGINT REFERENCES fotmob_original(id),
    PRIMARY KEY (match_id, capturado_en)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_fotmob_previo_ventana ON fotmob_previo (match_id, ventana);

CREATE TABLE IF NOT EXISTS fotmob_jugador_previo (
    match_id      TEXT NOT NULL,
    capturado_en  TIMESTAMPTZ NOT NULL,
    side          TEXT NOT NULL CHECK (side IN ('home', 'away')),
    jugador_id    BIGINT NOT NULL,
    nombre        TEXT,
    titular       BOOLEAN NOT NULL,
    posicion_id   INTEGER,
    valor_mercado BIGINT,
    PRIMARY KEY (match_id, capturado_en, side, jugador_id),
    FOREIGN KEY (match_id, capturado_en) REFERENCES fotmob_previo(match_id, capturado_en)
);

CREATE TABLE IF NOT EXISTS fotmob_baja_previa (
    match_id      TEXT NOT NULL,
    capturado_en  TIMESTAMPTZ NOT NULL,
    side          TEXT NOT NULL CHECK (side IN ('home', 'away')),
    jugador_id    BIGINT NOT NULL,
    nombre        TEXT,
    valor_mercado BIGINT,
    tipo          TEXT,
    lesion_id     INTEGER,
    regreso_texto TEXT,
    regreso_fecha TIMESTAMPTZ,
    PRIMARY KEY (match_id, capturado_en, side, jugador_id),
    FOREIGN KEY (match_id, capturado_en) REFERENCES fotmob_previo(match_id, capturado_en)
);

CREATE TABLE IF NOT EXISTS fotmob_captura_log (
    id         BIGSERIAL PRIMARY KEY,
    corrida_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    accion     TEXT NOT NULL,
    detalle    JSONB,
    denegado   BOOLEAN NOT NULL DEFAULT false
);

COMMIT;
