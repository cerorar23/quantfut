-- Reactivación del titular, 8-nov-2026: LaLiga 2, Serie B, Allsvenskan y Super League suiza vuelven a captura.
-- Se retiraron el 25-oct (db/088) por huecos de xG y por resultados de PropLine; el 8-nov PropLine cotiza las cuatro
-- (soccer_spain_segunda_division, soccer_italy_serie_b, soccer_sweden_allsvenskan, soccer_swiss_super_league) y el
-- archivo de SofaScore trae estadísticas y mapa de tiros con xG de 4 temporadas (23/24 → 26/27).
-- Ligue 2 y Superliga danesa SIGUEN fuera: PropLine no las cotiza (db/086).
-- `model_enabled` queda en FALSE a propósito: el motor solo las predice y publica cuando el backtest walk-forward
-- (docs/backtest_ligas_nuevas_*.md) pase la puerta; ahí se enciende en su propia migración.
-- Suiza: PropLine no entrega sus resultados (3 de 3 `expired`), salen de SofaScore.
BEGIN;
UPDATE leagues SET active = TRUE, captura_completa = TRUE, model_enabled = FALSE
 WHERE league_id IN ('es.laliga2', 'it.serie_b', 'se.allsvenskan', 'ch.super_league');
DO $$ BEGIN
  IF (SELECT count(*) FROM leagues WHERE active AND NOT model_enabled
        AND league_id IN ('es.laliga2', 'it.serie_b', 'se.allsvenskan', 'ch.super_league')) <> 4 THEN
    RAISE EXCEPTION 'db/105: no están las 4 ligas en el catálogo';
  END IF;
END $$;
COMMIT;
