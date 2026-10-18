-- 078: calendario de cada equipo en TODAS las competiciones (descanso y carga, F12), de API-Football.
--
-- `matches` solo guarda las 23 ligas y las dos copas europeas; un equipo que jugó la Copa del Rey, la FA Cup,
-- la Libertadores o un amistoso aparece "descansado" si solo se mira `matches`. Esta tabla trae el resto.
-- Una fila por (partido, equipo). Se actualiza en las temporadas en curso (estado, marcador, hora), por eso no es
-- inmutable. Equipos nacionales no incluidos: la API los devuelve por separado.
BEGIN;

CREATE TABLE IF NOT EXISTS calendario_equipo (
    af_fixture_id   BIGINT NOT NULL,
    af_team_id      BIGINT NOT NULL,
    team_id         BIGINT REFERENCES teams(team_id),
    fecha           TIMESTAMPTZ NOT NULL,
    temporada       INTEGER NOT NULL,
    liga_af_id      INTEGER NOT NULL,
    liga_nombre     TEXT,
    pais            TEXT,
    ronda           TEXT,
    local           BOOLEAN NOT NULL,
    rival_af_id     BIGINT,
    rival_nombre    TEXT,
    estado          TEXT,                 -- NS, FT, AET, PEN, PST, CANC...
    goles_favor     INTEGER,
    goles_contra    INTEGER,
    recibido_en     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (af_fixture_id, af_team_id)
);
CREATE INDEX IF NOT EXISTS idx_calendario_equipo_fecha ON calendario_equipo (team_id, fecha);

CREATE TABLE IF NOT EXISTS calendario_equipo_log (
    af_team_id   BIGINT NOT NULL,
    temporada    INTEGER NOT NULL,
    recibido_en  TIMESTAMPTZ NOT NULL DEFAULT now(),
    partidos     INTEGER NOT NULL,
    PRIMARY KEY (af_team_id, temporada)
);

COMMIT;
