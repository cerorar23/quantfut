-- ============================================================================
-- 041 - Líneas de goles en af_odds_snapshots (2026-10-06)
--
-- La misma petición /odds de API-Football trae, además del 1X2, "Goals
-- Over/Under" de Pinnacle y de las casas blandas. La línea de alta
-- probabilidad los necesita: a las 08:00 UTC el precio reciente de Pinnacle
-- casi siempre es de API-Football (ver harness/progreso.md, 2026-10-06).
--
-- `line` NULL en el 1X2. El UNIQUE de 016 no lleva la línea: dos líneas del
-- mismo lado chocarían. Se sustituye por un índice único con la línea y
-- NULLS NOT DISTINCT (PostgreSQL 15+) para que el 1X2, con línea NULL, siga
-- sin duplicarse. ADD COLUMN e índices no chocan con el trigger de
-- inmutabilidad (bloquea UPDATE/DELETE de filas, no DDL).
-- ============================================================================
BEGIN;

ALTER TABLE af_odds_snapshots ADD COLUMN IF NOT EXISTS line REAL;
COMMENT ON COLUMN af_odds_snapshots.line IS
  'Línea de goles en market = totals (1.5, 2.75...). NULL en h2h.';

CREATE UNIQUE INDEX IF NOT EXISTS af_odds_snapshots_uq_linea
    ON af_odds_snapshots (match_id, bookmaker, market, selection, line, provider_updated_at)
    NULLS NOT DISTINCT;

ALTER TABLE af_odds_snapshots
    DROP CONSTRAINT IF EXISTS af_odds_snapshots_match_id_bookmaker_market_selection_provi_key;

COMMIT;
