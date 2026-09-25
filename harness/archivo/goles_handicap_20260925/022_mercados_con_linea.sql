-- ============================================================================
-- 022 - Goles y hándicap en el criterio sharp: la LÍNEA entra en las tablas
--
-- Hasta ahora solo había 1X2, así que ni `af_odds_snapshots` ni
-- `sharp_shadow_offers` tenían línea. Con goles (totals) y hándicap asiático
-- (spreads) la misma casa, mercado y selección aparece en varias líneas del
-- mismo snapshot (más de 2,5 y más de 2,75): sin la línea en la clave única,
-- la segunda se descartaría en silencio por el ON CONFLICT.
--
-- Convención de línea, la misma que The Odds API y `eval/clv`:
--   totals   línea del total (2.5, 2.75...)
--   spreads  línea PROPIA de cada lado: local -0.5 / visitante +0.5
--   h2h      NULL
--
-- NULLS NOT DISTINCT (PG15+): sin eso dos filas 1X2 con line NULL no chocan
-- y la deduplicación del 1X2 dejaría de funcionar. Las dos tablas son
-- inmutables (trigger deny_mutation): ADD COLUMN no toca filas, así que no lo
-- dispara; las filas existentes quedan con line NULL, que es su valor correcto.
--
-- Los DROP CONSTRAINT van SIN `IF EXISTS` a propósito: los nombres los genera
-- Postgres truncados a 63 caracteres (comprobados en producción el
-- 2026-09-25). Con IF EXISTS un nombre mal escrito pasaría sin error, la clave
-- vieja seguiría viva y rechazaría la segunda línea del mismo snapshot. Mejor
-- que la migración falle entera (va en una transacción).
-- ============================================================================
BEGIN;

ALTER TABLE af_odds_snapshots ADD COLUMN IF NOT EXISTS line REAL;
ALTER TABLE af_odds_snapshots
    DROP CONSTRAINT af_odds_snapshots_match_id_bookmaker_market_selection_provi_key;
CREATE UNIQUE INDEX IF NOT EXISTS uq_af_odds_linea
    ON af_odds_snapshots (match_id, bookmaker, market, selection, line, provider_updated_at)
    NULLS NOT DISTINCT;

ALTER TABLE sharp_shadow_offers ADD COLUMN IF NOT EXISTS line REAL;
ALTER TABLE sharp_shadow_offers
    DROP CONSTRAINT sharp_shadow_offers_match_id_book_market_selection_odds_sou_key;
CREATE UNIQUE INDEX IF NOT EXISTS uq_sombra_sharp_linea
    ON sharp_shadow_offers (match_id, book, market, selection, line, odds_source, odds_as_of)
    NULLS NOT DISTINCT;

COMMIT;
