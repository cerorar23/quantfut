-- ============================================================================
-- 039 - Stake encogido por la incertidumbre de la persistencia (idea 5,
-- 2026-10-03; Baker y McHale, 2013)
--
-- `stake_units` CONSERVA su significado: Kelly sobre el edge esperado, SIN el
-- factor. Es lo que decide qué oferta es publicable y, por tanto, la muestra
-- de la puerta comercial; el usuario decidió que eso no cambie ("stake sí,
-- muestra no"). Lo que se publicaría lleva el factor y va aparte.
-- Nullable: las ofertas anteriores no tienen factor (equivale a 1).
-- ADD COLUMN: el trigger de inmutabilidad no se toca.
-- ============================================================================
BEGIN;

ALTER TABLE sharp_shadow_offers
    ADD COLUMN IF NOT EXISTS stake_publicado_units REAL,
    ADD COLUMN IF NOT EXISTS factor_incertidumbre REAL;
COMMENT ON COLUMN sharp_shadow_offers.stake_publicado_units IS
  'stake_units × factor_incertidumbre: lo que se habría recomendado apostar.';
COMMENT ON COLUMN sharp_shadow_offers.factor_incertidumbre IS
  'ρ²/(ρ²+SE²) de la casa ese día (picks.factores).';

COMMIT;
