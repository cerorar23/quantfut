-- 9-nov-2026: encender el modelo en las ligas que aprobaron el backtest (docs/backtest_ligas_nuevas_20261109.md).
-- Criterios C1-C4 fijados antes de medir. Aprueban: Turquía, LaLiga 2, Serie B y Allsvenskan.
-- Quedan apagadas: Noruega y Suiza (fallan C3 por 0,003; se vuelven a medir con más partidos), Championship y 2. Bundesliga
-- (el modelo no mejora a la frecuencia de la liga).
-- Requisitos ANTES de aplicarla: db/105 aplicada (LaLiga 2, Serie B y Allsvenskan vuelven a estar activas), el modelo
-- entrenado con estas ligas ya subido y activo (`scripts/entrenamiento_local/subir.sh --activar`), y `FUTBOL`/scraper del VPS
-- capturando esas ligas. Con el interruptor encendido y el modelo viejo activo, el job diario sellaría predicciones de
-- equipos que no conoce (db/033).
BEGIN;
UPDATE leagues SET model_enabled = TRUE
 WHERE league_id IN ('tr.super_lig', 'es.laliga2', 'it.serie_b', 'se.allsvenskan') AND active;
DO $$ BEGIN
  IF (SELECT count(*) FROM leagues WHERE model_enabled
        AND league_id IN ('tr.super_lig', 'es.laliga2', 'it.serie_b', 'se.allsvenskan')) <> 4 THEN
    RAISE EXCEPTION 'db/106: las 4 ligas deben estar activas (aplica antes db/105)';
  END IF;
END $$;
COMMIT;
