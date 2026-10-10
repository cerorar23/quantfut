-- ============================================================================
-- 048 - Córners de cada equipo (decisión del usuario, 2026-10-09) en la
-- escalera y en la línea de alta probabilidad. Las cuotas llegan de
-- API-Football (bets 57/58) a af_odds_snapshots, que no restringe `market`.
-- Mismo patrón que 046 y 047: un solo CHECK sobre `market` por tabla.
-- ============================================================================
BEGIN;

ALTER TABLE escalera_pasos DROP CONSTRAINT IF EXISTS escalera_pasos_market_check;
ALTER TABLE escalera_pasos ADD CONSTRAINT escalera_pasos_market_check
    CHECK (market IN ('h2h', 'totals', 'team_totals_home', 'team_totals_away', 'spreads',
                      'btts', 'corners', 'cards', 'corners_home', 'corners_away'));

ALTER TABLE alta_prob_picks DROP CONSTRAINT IF EXISTS alta_prob_picks_market_check;
ALTER TABLE alta_prob_picks ADD CONSTRAINT alta_prob_picks_market_check
    CHECK (market IN ('h2h', 'double_chance', 'totals',
                      'team_totals_home', 'team_totals_away',
                      'btts', 'spreads', 'corners', 'corners_home', 'corners_away'));

COMMENT ON COLUMN alta_prob_results.valor IS
    'Córners con los que se liquidó: del partido (corners) o de un equipo (corners_home/away). NULL en los demás mercados.';

DO $$ BEGIN
  IF (SELECT count(*) FROM pg_constraint
      WHERE conrelid = 'escalera_pasos'::regclass AND contype = 'c'
        AND pg_get_constraintdef(oid) LIKE '%market%') <> 1 THEN
    RAISE EXCEPTION 'escalera_pasos tiene más de un CHECK sobre market: revisar db/048';
  END IF;
  IF (SELECT count(*) FROM pg_constraint
      WHERE conrelid = 'alta_prob_picks'::regclass AND contype = 'c'
        AND pg_get_constraintdef(oid) LIKE '%market%') <> 1 THEN
    RAISE EXCEPTION 'alta_prob_picks tiene más de un CHECK sobre market: revisar db/048';
  END IF;
END $$;

COMMIT;
