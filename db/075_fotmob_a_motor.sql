-- 075: contexto de partido, jugadores y bajas del archivo FotMob, con clave match_id.
--
-- Por qué tablas propias y no lineups_historicas / estadisticas_jugador: esas llevan identificadores de
-- API-Football (player_id) y FotMob usa los suyos. Mezclarlos rompería player_ratings y lineup_challenger.
-- El puente de identidades (F4) se hará aparte. Fuente: historical_football_matches (provider='fotmob'),
-- que es un archivo inmutable: estas tablas se pueden regenerar y se cargan con ON CONFLICT DO NOTHING.
--
-- Todo viene de páginas guardadas DESPUÉS del partido (recibido_en > saque). Las listas de no disponibles son
-- la reconstrucción de quién faltó, no lo que se sabía antes del partido: sirven para entrenar y medir, y
-- cualquier consumidor tiene que aplicar su propia regla de point-in-time.
BEGIN;

CREATE TABLE IF NOT EXISTS fotmob_partido (
    match_id            TEXT PRIMARY KEY REFERENCES matches(match_id),
    source_match_id     TEXT NOT NULL,
    raw_sha256          TEXT NOT NULL,
    recibido_en         TIMESTAMPTZ NOT NULL,
    ronda               TEXT,
    ronda_nombre        TEXT,
    ida_vuelta          JSONB,            -- legInfo tal cual (marcador global en eliminatorias)
    perdedor_global     TEXT,             -- header.status.whoLostOnAggregated
    arbitro             TEXT,
    arbitro_pais        TEXT,
    asistencia          INTEGER,
    estadio             TEXT,
    formacion_local     TEXT,
    formacion_visita    TEXT,
    rating_local        REAL,
    rating_visita       REAL,
    valor_xi_local      BIGINT,           -- suma del valor de mercado de los titulares, en euros
    valor_xi_visita     BIGINT,
    edad_xi_local       REAL,
    edad_xi_visita      REAL,
    entrenador_local_id     BIGINT,
    entrenador_local        TEXT,
    entrenador_visita_id    BIGINT,
    entrenador_visita       TEXT,
    clima_temperatura_c REAL,
    clima_viento        REAL,
    clima_direccion     TEXT,
    clima_humedad       REAL,
    clima_precipitacion REAL,
    clima_nubosidad     REAL,
    clima_descripcion   TEXT,
    clima_api           TEXT,             -- current | historical | forecast, según FotMob
    clima_actualizado   TIMESTAMPTZ,
    clima_desfase_horas REAL,             -- actualizado - saque
    clima_en_partido    BOOLEAN           -- true si el dato cae entre 1 h antes y 3 h después del saque
);

CREATE TABLE IF NOT EXISTS fotmob_jugador_partido (
    match_id        TEXT NOT NULL REFERENCES matches(match_id),
    side            TEXT NOT NULL CHECK (side IN ('home', 'away')),
    jugador_id      BIGINT NOT NULL,      -- id de FotMob, NO de API-Football
    nombre          TEXT,
    titular         BOOLEAN NOT NULL,
    posicion_id     INTEGER,
    posicion_habitual_id INTEGER,
    camiseta        TEXT,
    edad            INTEGER,
    valor_mercado   BIGINT,               -- euros
    rating          REAL,
    PRIMARY KEY (match_id, side, jugador_id)
);

CREATE TABLE IF NOT EXISTS fotmob_baja (
    match_id        TEXT NOT NULL REFERENCES matches(match_id),
    side            TEXT NOT NULL CHECK (side IN ('home', 'away')),
    jugador_id      BIGINT NOT NULL,
    nombre          TEXT,
    edad            INTEGER,
    posicion_id     INTEGER,
    valor_mercado   BIGINT,
    tipo            TEXT,                 -- injury | suspension | ...
    lesion_id       INTEGER,
    regreso_texto   TEXT,                 -- p. ej. Doubtful, Out for season
    regreso_fecha   TIMESTAMPTZ,
    PRIMARY KEY (match_id, side, jugador_id)
);

CREATE INDEX IF NOT EXISTS idx_fotmob_jugador_partido_jugador ON fotmob_jugador_partido (jugador_id);
CREATE INDEX IF NOT EXISTS idx_fotmob_baja_jugador ON fotmob_baja (jugador_id);

-- Minutos y estadísticas por jugador siguen en historical_football_player_stats; esta vista los une.
CREATE OR REPLACE VIEW v_fotmob_jugador_partido AS
SELECT j.*, ps.minutes AS minutos, ps.statistics AS estadisticas
FROM fotmob_jugador_partido j
JOIN fotmob_partido p USING (match_id)
LEFT JOIN historical_football_player_stats ps
       ON ps.provider = 'fotmob' AND ps.source_match_id = p.source_match_id
      AND ps.side = j.side AND ps.source_player_id = j.jugador_id;

COMMIT;
