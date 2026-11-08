-- ============================================================================
-- 099 - Retos escalera: 6 objetivos de cuota y mercados multideporte
--
-- Redisenio del reto escalera (2026-11-08):
-- 1. Objetivos de cuota (5.5, 10.2, 15.3, 20.5, 30.3, 40.2) con tope de 10 escalones.
-- 2. Nuevos mercados de baja varianza: double_chance, props NBA (player_points,
--    player_rebounds, player_assists, player_threes) y tenis (handicap_games, total_games).
-- ============================================================================
BEGIN;

ALTER TABLE escalera_retos ADD COLUMN IF NOT EXISTS target_cuota REAL;
COMMENT ON COLUMN escalera_retos.target_cuota IS
    'Multiplo objetivo de cobro (5.5, 10.2, 15.3, 20.5, 30.3, 40.2); NULL = regla anterior';

ALTER TABLE escalera_pasos DROP CONSTRAINT IF EXISTS escalera_pasos_market_check;
ALTER TABLE escalera_pasos ADD CONSTRAINT escalera_pasos_market_check
    CHECK (market IN ('h2h', 'totals', 'team_totals_home', 'team_totals_away', 'spreads',
                      'btts', 'corners', 'cards', 'corners_home', 'corners_away',
                      'double_chance', 'player_points', 'player_rebounds', 'player_assists',
                      'player_threes', 'handicap_games', 'total_games'));

COMMIT;
