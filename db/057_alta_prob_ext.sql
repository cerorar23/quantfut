-- ============================================================================
-- 057 - Alta probabilidad ampliada: 62-95 %, todos los candidatos aprobados por
-- partido y mercado (decisión del usuario, 2026-10-11). Tabla APARTE de
-- `alta_prob_picks` (un pick por partido, 80-95 %), que no se toca.
--
-- Qué entra lo fija la prueba histórica de los tramos 62-80 %
-- (`eval/alta_prob_calibracion.py --amplio`, `alta_prob.EXT_*`). Inmutables y
-- selladas en el lote (`alta_ext`, `hashchain.LOTE_ALTA_EXT_DESDE`).
-- ============================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS alta_prob_ext (
    ext_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id     TEXT NOT NULL REFERENCES matches(match_id),
    market       TEXT NOT NULL CHECK (market IN ('h2h', 'double_chance', 'totals',
                      'team_totals_home', 'team_totals_away', 'btts', 'spreads',
                      'corners', 'corners_home', 'corners_away')),
    selection    TEXT NOT NULL,
    line         REAL,
    prob         DOUBLE PRECISION NOT NULL CHECK (prob >= 0.62 AND prob <= 0.95),
    fair_price   REAL NOT NULL,
    ref_price    REAL,
    ref_book     TEXT,
    odds_source  TEXT NOT NULL,
    odds_as_of   TIMESTAMPTZ NOT NULL,
    fit          JSONB,
    decided_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT alta_prob_ext_uq UNIQUE NULLS NOT DISTINCT (match_id, market, selection, line)
);
CREATE INDEX IF NOT EXISTS idx_alta_prob_ext_decided ON alta_prob_ext(decided_at);

DROP TRIGGER IF EXISTS trg_alta_prob_ext_immutable ON alta_prob_ext;
CREATE TRIGGER trg_alta_prob_ext_immutable
    BEFORE UPDATE OR DELETE ON alta_prob_ext
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();

CREATE TABLE IF NOT EXISTS alta_prob_ext_results (
    ext_id      UUID PRIMARY KEY REFERENCES alta_prob_ext(ext_id),
    outcome     TEXT NOT NULL CHECK (outcome IN ('win', 'loss', 'push', 'void')),
    home_goals  SMALLINT NOT NULL,
    away_goals  SMALLINT NOT NULL,
    valor       SMALLINT,
    settled_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_alta_prob_ext_results_immutable ON alta_prob_ext_results;
CREATE TRIGGER trg_alta_prob_ext_results_immutable
    BEFORE UPDATE OR DELETE ON alta_prob_ext_results
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();

COMMIT;
