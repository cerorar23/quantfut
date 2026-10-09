-- ============================================================================
-- 047 - Línea de alta probabilidad: ambos marcan, hándicap asiático y córners
-- (decisión del usuario, 2026-10-09). Más/menos 2,5 ya cabía en 'totals'.
--
-- - Mercados nuevos en alta_prob_picks.
-- - Resultados: 'push' (hándicap entero devuelto) y 'void' (córners sin
--   estadística 72 h después del partido). Ninguno de los dos cuenta en el
--   historial ni en el control: la probabilidad del hándicap es la de ganar
--   condicionada a que no haya devolución.
-- - `valor`: total de córners con el que se liquidó.
-- Mismo patrón que 042: el CHECK de la columna se llama <tabla>_<col>_check y
-- la guardia aborta si queda otro CHECK sobre la misma columna.
-- ============================================================================
BEGIN;

ALTER TABLE alta_prob_picks DROP CONSTRAINT IF EXISTS alta_prob_picks_market_check;
ALTER TABLE alta_prob_picks ADD CONSTRAINT alta_prob_picks_market_check
    CHECK (market IN ('h2h', 'double_chance', 'totals',
                      'team_totals_home', 'team_totals_away',
                      'btts', 'spreads', 'corners'));

ALTER TABLE alta_prob_results DROP CONSTRAINT IF EXISTS alta_prob_results_outcome_check;
ALTER TABLE alta_prob_results ADD CONSTRAINT alta_prob_results_outcome_check
    CHECK (outcome IN ('win', 'loss', 'push', 'void'));

ALTER TABLE alta_prob_results ADD COLUMN IF NOT EXISTS valor SMALLINT;

COMMENT ON COLUMN alta_prob_picks.line IS
    'Goles (1,5 / 2,5 / 3,5), goles de un equipo (0,5), hándicap del lado elegido (+1,5 = recibe 1,5) o córners. NULL en 1X2, doble oportunidad y ambos marcan.';
COMMENT ON COLUMN alta_prob_results.valor IS
    'Córners totales del partido con los que se liquidó. NULL en los demás mercados.';

DO $$ BEGIN
  IF (SELECT count(*) FROM pg_constraint
      WHERE conrelid = 'alta_prob_picks'::regclass AND contype = 'c'
        AND pg_get_constraintdef(oid) LIKE '%market%') <> 1 THEN
    RAISE EXCEPTION 'alta_prob_picks tiene más de un CHECK sobre market: revisar db/047';
  END IF;
  IF (SELECT count(*) FROM pg_constraint
      WHERE conrelid = 'alta_prob_results'::regclass AND contype = 'c'
        AND pg_get_constraintdef(oid) LIKE '%outcome%') <> 1 THEN
    RAISE EXCEPTION 'alta_prob_results tiene más de un CHECK sobre outcome: revisar db/047';
  END IF;
END $$;

COMMIT;
