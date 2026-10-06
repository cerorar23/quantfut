-- ============================================================================
-- 040 - Línea de alta probabilidad (decisión del usuario, 2026-10-05)
--
-- Pronósticos con probabilidad real (Pinnacle sin margen) entre el 80 y el
-- 95 %, uno por partido, aparte de los picks de valor: ni `picks` ni su puerta
-- comercial se tocan. Diseño:
-- docs/superpowers/specs/2026-10-05-linea-alta-probabilidad-design.md
--
-- Inmutables como `picks`: un pronóstico fallado no se borra ni se corrige.
-- `prob` en DOUBLE PRECISION: con REAL, el redondeo podía dejar un 0,80
-- justo por debajo del CHECK.
-- ============================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS alta_prob_picks (
    alta_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id     TEXT NOT NULL UNIQUE REFERENCES matches(match_id),
    market       TEXT NOT NULL CHECK (market IN ('h2h', 'double_chance', 'totals')),
    selection    TEXT NOT NULL,
    line         REAL,                        -- solo goles (1,5 / 3,5 / 4,5)
    prob         DOUBLE PRECISION NOT NULL CHECK (prob >= 0.80 AND prob <= 0.95),
    fair_price   REAL NOT NULL,               -- 1 / prob
    ref_price    REAL,                        -- mejor cuota de SOFT_BOOKS en el mismo snapshot
    ref_book     TEXT,
    odds_source  TEXT NOT NULL,               -- 'the_odds_api' | 'api_football'
    odds_as_of   TIMESTAMPTZ NOT NULL,        -- hora del precio de Pinnacle
    fit          JSONB,                       -- goles: lambdas, rho, línea y residuo del ajuste
    decided_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_alta_prob_decided ON alta_prob_picks(decided_at);

DROP TRIGGER IF EXISTS trg_alta_prob_immutable ON alta_prob_picks;
CREATE TRIGGER trg_alta_prob_immutable
    BEFORE UPDATE OR DELETE ON alta_prob_picks
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();

CREATE TABLE IF NOT EXISTS alta_prob_results (
    alta_id     UUID PRIMARY KEY REFERENCES alta_prob_picks(alta_id),
    outcome     TEXT NOT NULL CHECK (outcome IN ('win', 'loss')),
    home_goals  SMALLINT NOT NULL,
    away_goals  SMALLINT NOT NULL,
    settled_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_alta_prob_results_immutable ON alta_prob_results;
CREATE TRIGGER trg_alta_prob_results_immutable
    BEFORE UPDATE OR DELETE ON alta_prob_results
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();

COMMIT;
