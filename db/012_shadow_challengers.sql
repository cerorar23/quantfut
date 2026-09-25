-- ============================================================================
-- Challengers en sombra: predicen y miden CLV, pero jamás publican apuestas.
-- ============================================================================

CREATE TABLE IF NOT EXISTS shadow_predictions (
    shadow_prediction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id             TEXT NOT NULL REFERENCES matches(match_id),
    base_prediction_id   UUID REFERENCES predictions(prediction_id),
    challenger           TEXT NOT NULL,
    model_version        TEXT NOT NULL,
    generated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    as_of                TIMESTAMPTZ NOT NULL,
    home_lambda          REAL NOT NULL,
    away_lambda          REAL NOT NULL,
    rho                  REAL NOT NULL DEFAULT 0,
    probabilities        JSONB NOT NULL,
    features             JSONB NOT NULL,
    UNIQUE (match_id, challenger, model_version)
);
CREATE INDEX IF NOT EXISTS idx_shadow_pred_match
    ON shadow_predictions(match_id, generated_at DESC);

CREATE TABLE IF NOT EXISTS shadow_picks (
    shadow_pick_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shadow_prediction_id UUID NOT NULL REFERENCES shadow_predictions(shadow_prediction_id),
    match_id             TEXT NOT NULL REFERENCES matches(match_id),
    market               TEXT NOT NULL,
    selection            TEXT NOT NULL,
    line                 REAL,
    model_prob           REAL NOT NULL,
    observed_price       REAL NOT NULL,
    bookmaker            TEXT NOT NULL,
    raw_edge_pct         REAL NOT NULL,
    edge_pct             REAL NOT NULL,
    captured_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (shadow_prediction_id, market, selection, line)
);
CREATE INDEX IF NOT EXISTS idx_shadow_picks_match ON shadow_picks(match_id);

CREATE TABLE IF NOT EXISTS shadow_results (
    shadow_pick_id       UUID PRIMARY KEY REFERENCES shadow_picks(shadow_pick_id),
    closing_price        REAL,
    closing_prob_devig   REAL,
    clv_pct              REAL,
    beat_close           BOOLEAN,
    outcome              TEXT,
    settled_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_shadow_pred_immutable ON shadow_predictions;
CREATE TRIGGER trg_shadow_pred_immutable
    BEFORE UPDATE OR DELETE ON shadow_predictions
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();

DROP TRIGGER IF EXISTS trg_shadow_picks_immutable ON shadow_picks;
CREATE TRIGGER trg_shadow_picks_immutable
    BEFORE UPDATE OR DELETE ON shadow_picks
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();
