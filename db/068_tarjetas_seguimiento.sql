-- ============================================================================
-- 068 - Seguimiento sin publicar de los candidatos de tarjetas (2026-10-14)
--
-- Las tarjetas dominan los tickets del parley y casi no tienen historial propio:
-- ni la alta probabilidad ni la escalera las han liquidado en número (2 patas del
-- parley). Esta tabla guarda cada día TODOS los candidatos de tarjetas con la
-- probabilidad que usaría el parley (la menor entre modelo y mercado) y su cuota,
-- para medir prometido frente a real cuanto antes. NO SE PUBLICA: ninguna ruta
-- de la API ni de la app la lee. Inmutable y sellada en el lote
-- (`tarjetas_seg`, `hashchain.LOTE_TARJETAS_DESDE`), como `alta_prob_ext`.
-- ============================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS tarjetas_seg (
    seg_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id     TEXT NOT NULL REFERENCES matches(match_id),
    market       TEXT NOT NULL CHECK (market = 'cards'),
    selection    TEXT NOT NULL CHECK (selection IN ('over', 'under')),
    line         REAL NOT NULL,
    prob         DOUBLE PRECISION NOT NULL CHECK (prob > 0 AND prob < 1),  -- min(modelo, mercado)
    fair_price   REAL NOT NULL,                  -- 1 / prob
    ref_price    REAL NOT NULL CHECK (ref_price > 1),  -- mejor cuota de SOFT_BOOKS: sin cuota no es tomable
    ref_book     TEXT NOT NULL,
    odds_source  TEXT NOT NULL,
    odds_as_of   TIMESTAMPTZ NOT NULL,
    fit          JSONB,                          -- modelo, mercado y lambdas
    decided_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT tarjetas_seg_uq UNIQUE (match_id, market, selection, line)
);
CREATE INDEX IF NOT EXISTS idx_tarjetas_seg_decided ON tarjetas_seg(decided_at);

DROP TRIGGER IF EXISTS trg_tarjetas_seg_immutable ON tarjetas_seg;
CREATE TRIGGER trg_tarjetas_seg_immutable
    BEFORE UPDATE OR DELETE ON tarjetas_seg
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();

CREATE TABLE IF NOT EXISTS tarjetas_seg_results (
    seg_id      UUID PRIMARY KEY REFERENCES tarjetas_seg(seg_id),
    -- 'void': partido aplazado o sin estadísticas pasado el margen. 'push': total igual a la línea.
    outcome     TEXT NOT NULL CHECK (outcome IN ('win', 'loss', 'push', 'void')),
    home_goals  SMALLINT,
    away_goals  SMALLINT,
    valor       SMALLINT,                        -- tarjetas del partido (amarillas + rojas)
    settled_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK ((outcome = 'void') = (home_goals IS NULL))
);

DROP TRIGGER IF EXISTS trg_tarjetas_seg_results_immutable ON tarjetas_seg_results;
CREATE TRIGGER trg_tarjetas_seg_results_immutable
    BEFORE UPDATE OR DELETE ON tarjetas_seg_results
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qf_readonly') THEN
    GRANT SELECT ON tarjetas_seg, tarjetas_seg_results TO qf_readonly;
  END IF;
END $$;

COMMIT;
