-- ============================================================================
-- 103 - Reto escalera por objetivo de cobro (rediseño del 2026-11-07/08)
--
-- `target_cuota`: múltiplo de cobro que persigue el reto (2,0 · 2,8 · 4,5 · 7,5 · 12 ·
-- 20); NULL = reto de la regla anterior (80 % en 7 días o más antigua).
-- Mercado nuevo en los escalones: `double_chance`.
-- Añadir una columna NULL no dispara los triggers de inmutabilidad (son de filas).
-- ============================================================================
BEGIN;

ALTER TABLE escalera_retos ADD COLUMN IF NOT EXISTS target_cuota REAL
    CHECK (target_cuota IS NULL OR target_cuota > 1);
COMMENT ON COLUMN escalera_retos.target_cuota IS
    'Múltiplo de cobro objetivo (2,0 · 2,8 · 4,5 · 7,5 · 12 · 20); NULL = regla anterior';

ALTER TABLE escalera_pasos DROP CONSTRAINT IF EXISTS escalera_pasos_market_check;
ALTER TABLE escalera_pasos ADD CONSTRAINT escalera_pasos_market_check
    CHECK (market IN ('h2h', 'totals', 'team_totals_home', 'team_totals_away', 'spreads',
                      'btts', 'corners', 'cards', 'corners_home', 'corners_away',
                      'double_chance'));

COMMIT;
