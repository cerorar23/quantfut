-- Doble oportunidad como mercado admitido en las patas del parley (cuota real de API-Football,
-- bet 12, capturada desde 2026-10-12). Solo AMPLÍA la regla: no toca ninguna fila.
BEGIN;
ALTER TABLE parley_patas DROP CONSTRAINT IF EXISTS parley_patas_market_check;
ALTER TABLE parley_patas ADD CONSTRAINT parley_patas_market_check
    CHECK (market IN ('h2h', 'double_chance', 'totals', 'team_totals_home', 'team_totals_away',
                      'spreads', 'btts', 'corners', 'cards', 'corners_home', 'corners_away'));
COMMIT;
