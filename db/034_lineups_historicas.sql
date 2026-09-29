-- ============================================================================
-- 034 - Alineaciones históricas, SOLO para entrenar el ajuste por XI
--
-- Decisión del usuario (2026-09-29). El challenger de XI exige 700 partidos
-- con predicción sellada y XI capturado antes del inicio; en vivo no se
-- llegaría hasta diciembre. Estas alineaciones se descargan DESPUÉS del
-- partido (el XI publicado a T-60 casi siempre coincide con el que devuelve
-- el proveedor al terminar), así que no cumplen el punto en el tiempo de
-- `lineups` y viven en una tabla aparte:
--   * las lee únicamente `model.lineup_challenger` para entrenar y validar
--     fuera de muestra;
--   * la predicción diaria, la sombra y `lineups.availability()` NO la leen:
--     lo sellado y lo medido contra el cierre sigue usando solo XI capturados
--     antes del partido.
-- `starters` vacío = el proveedor no tenía XI: se guarda para no volver a
-- gastar una petición en ese partido, y el entrenamiento lo descarta.
-- ============================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS lineups_historicas (
    match_id       TEXT NOT NULL REFERENCES matches(match_id),
    side           TEXT NOT NULL CHECK (side IN ('home', 'away')),
    formation      TEXT,
    starters       JSONB NOT NULL,
    af_fixture_id  INTEGER NOT NULL,
    fetched_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (match_id, side)
);
COMMENT ON TABLE lineups_historicas IS
  'XI descargados después del partido. Solo para entrenar/validar el '
  'challenger de XI; nunca para predecir, sellar ni la sombra (db/034).';

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qf_readonly') THEN
    GRANT SELECT ON lineups_historicas TO qf_readonly;
  END IF;
END $$;

COMMIT;
