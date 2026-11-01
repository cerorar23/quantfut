-- 091: xG corregido de los partidos cuyo xG se guardó antes de XG_MIN_HORAS (20 h) del saque.
--
-- El xG se corrige después del partido (28-oct-2026: Houston 0-0 se guardó como 0,00-0,03 y hoy da 0,81-1,38). Lo ya
-- guardado en `matches` NO se reescribe (es un dato con fecha de recepción que usa el entrenamiento); aquí queda, por
-- partido, la primera lectura tomada pasada la hora mínima, con el original al lado para poder medir si importa
-- (entrenar con uno y con otro). Solo se añade; inmutable como los originales.

CREATE TABLE IF NOT EXISTS xg_corregido (
    match_id            TEXT PRIMARY KEY REFERENCES matches(match_id),
    fuente              TEXT NOT NULL CHECK (fuente IN ('fotmob')),
    home_xg             REAL NOT NULL CHECK (home_xg >= 0),
    away_xg             REAL NOT NULL CHECK (away_xg >= 0),
    capturado_en        TIMESTAMPTZ NOT NULL,   -- hora real de la página de la que sale el valor corregido
    original_fuente     TEXT,
    original_home_xg    REAL NOT NULL,
    original_away_xg    REAL NOT NULL,
    original_recibido   TIMESTAMPTZ NOT NULL,   -- matches.xg_recorded_at del valor original
    registrado_en       TIMESTAMPTZ NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_xg_corregido_immutable ON xg_corregido;
CREATE TRIGGER trg_xg_corregido_immutable
    BEFORE UPDATE OR DELETE ON xg_corregido
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();

-- Reversión: DROP TABLE xg_corregido;
