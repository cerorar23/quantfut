-- ============================================================================
-- 026 - Una sola etiqueta de temporada por temporada
--
-- El calendario de API-Football etiquetaba '2026' (Brasil, Argentina, MLS) y
-- '2026A' (Liga MX) lo que el histórico de football-data etiqueta '2627'.
-- `fixtures._season_label` ya usa la convención del histórico; esto corrige
-- las filas creadas antes del cambio.
--
-- Solo cambia la COLUMNA `season`, no el match_id (que la lleva dentro como
-- texto opaco y lo referencian predicciones, picks y cuotas inmutables). El
-- calendario encuentra los partidos existentes por su id de API-Football, así
-- que no se duplica ninguno. `matches` no tiene trigger de inmutabilidad: la
-- ingesta de resultados ya la actualiza a diario.
-- ============================================================================
BEGIN;

UPDATE matches SET season = '2627'
WHERE external_ids ? 'api_football'
  AND league_id IN ('ar.primera', 'br.serie_a', 'us.mls')
  AND season = '2026';

UPDATE matches SET season = '2627'
WHERE external_ids ? 'api_football'
  AND league_id = 'mx.liga_mx'
  AND season IN ('2026A', '2027C');

COMMIT;
