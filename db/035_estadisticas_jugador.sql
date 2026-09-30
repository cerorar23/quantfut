-- ============================================================================
-- 035 - Estadísticas por jugador y partido (fuerza por jugador, Fase A)
--
-- Diseño: docs/superpowers/specs/2026-09-29-fuerza-por-jugador-design.md.
-- Fuente: /fixtures/players de API-Football, 1 petición por partido. Datos de
-- partidos YA jugados: la Fase B solo usará, para un partido del día D, filas
-- de partidos anteriores a D. `nota_proveedor` puede revisarse días después:
-- solo comparación, con `fetched_at`.
-- `estadisticas_jugador_log` registra cada intento, también los vacíos, para
-- no gastar dos veces la petición de un partido sin datos.
-- ============================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS estadisticas_jugador (
    match_id        TEXT NOT NULL REFERENCES matches(match_id),
    side            TEXT NOT NULL CHECK (side IN ('home', 'away')),
    player_id       BIGINT NOT NULL,
    nombre          TEXT,
    posicion        TEXT,
    minutos         SMALLINT NOT NULL,
    titular         BOOLEAN NOT NULL,
    goles           SMALLINT NOT NULL,
    asistencias     SMALLINT NOT NULL,
    tiros           SMALLINT NOT NULL,
    tiros_puerta    SMALLINT NOT NULL,
    pases_clave     SMALLINT NOT NULL,
    regates         SMALLINT NOT NULL,
    entradas        SMALLINT NOT NULL,
    intercepciones  SMALLINT NOT NULL,
    duelos_ganados  SMALLINT NOT NULL,
    paradas         SMALLINT NOT NULL,
    nota_proveedor  REAL,
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (match_id, player_id)
);
CREATE INDEX IF NOT EXISTS idx_estad_jugador_player ON estadisticas_jugador (player_id);

CREATE TABLE IF NOT EXISTS estadisticas_jugador_log (
    match_id     TEXT PRIMARY KEY REFERENCES matches(match_id),
    n_jugadores  INTEGER NOT NULL,
    fetched_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qf_readonly') THEN
    GRANT SELECT ON estadisticas_jugador, estadisticas_jugador_log TO qf_readonly;
  END IF;
END $$;

COMMIT;
