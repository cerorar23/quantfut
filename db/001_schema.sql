-- ============================================================================
-- QUANTFUT - Esquema Postgres con corrección point-in-time e inmutabilidad
-- Postgres 15+
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- CATÁLOGO
-- ---------------------------------------------------------------------------

CREATE TABLE leagues (
    league_id       TEXT PRIMARY KEY,           -- 'mx.liga_mx'
    country         TEXT NOT NULL,
    name            TEXT NOT NULL,
    tier            SMALLINT NOT NULL DEFAULT 1,
    fd_code         TEXT,                       -- código football-data.co.uk (ej. 'E0')
    fd_extra        BOOLEAN NOT NULL DEFAULT FALSE,
    odds_api_key    TEXT,                       -- clave de The Odds API (ej. 'soccer_mexico_ligamx')
    fbref_id        TEXT,
    active          BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE teams (
    team_id         BIGSERIAL PRIMARY KEY,
    league_id       TEXT NOT NULL REFERENCES leagues(league_id),
    canonical_name  TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (league_id, canonical_name)
);

-- CRÍTICO: cada fuente escribe el nombre distinto. Sin esto, joins silenciosamente rotos.
CREATE TABLE team_aliases (
    alias           TEXT NOT NULL,
    source          TEXT NOT NULL,              -- 'football_data' | 'odds_api' | 'fbref' | 'api_football'
    team_id         BIGINT NOT NULL REFERENCES teams(team_id),
    PRIMARY KEY (alias, source)
);
CREATE INDEX idx_team_aliases_team ON team_aliases(team_id);

-- ---------------------------------------------------------------------------
-- PARTIDOS
-- ---------------------------------------------------------------------------

CREATE TABLE matches (
    match_id            TEXT PRIMARY KEY,       -- 'mx.liga_mx:2026:ame-cru:20260412'
    league_id           TEXT NOT NULL REFERENCES leagues(league_id),
    season              TEXT NOT NULL,
    kickoff_utc         TIMESTAMPTZ NOT NULL,
    home_team_id        BIGINT NOT NULL REFERENCES teams(team_id),
    away_team_id        BIGINT NOT NULL REFERENCES teams(team_id),
    status              TEXT NOT NULL DEFAULT 'scheduled',  -- scheduled|live|finished|postponed
    -- Resultado (NULL hasta que termina)
    home_goals          SMALLINT,
    away_goals          SMALLINT,
    home_goals_ht       SMALLINT,
    away_goals_ht       SMALLINT,
    home_xg             REAL,
    away_xg             REAL,
    home_shots          SMALLINT,
    away_shots          SMALLINT,
    home_shots_target   SMALLINT,
    away_shots_target   SMALLINT,
    home_corners        SMALLINT,
    away_corners        SMALLINT,
    -- Auditoría temporal
    ingested_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    result_recorded_at  TIMESTAMPTZ,
    xg_recorded_at      TIMESTAMPTZ,            -- los proveedores revisan xG días después
    external_ids        JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX idx_matches_kickoff   ON matches(kickoff_utc);
CREATE INDEX idx_matches_league_ko ON matches(league_id, kickoff_utc);
CREATE INDEX idx_matches_status    ON matches(status) WHERE status <> 'finished';

-- ---------------------------------------------------------------------------
-- CUOTAS TIMESTAMPED  <-- ESTE ES EL ACTIVO DEL NEGOCIO
-- Nunca se borra. Nunca se actualiza. Solo INSERT.
-- ---------------------------------------------------------------------------

CREATE TABLE odds_snapshots (
    snapshot_id     BIGSERIAL PRIMARY KEY,
    match_id        TEXT NOT NULL REFERENCES matches(match_id),
    bookmaker       TEXT NOT NULL,
    market          TEXT NOT NULL,              -- 'h2h' | 'totals' | 'spreads'
    selection       TEXT NOT NULL,              -- 'home'|'draw'|'away'|'over'|'under'
    line            REAL,                       -- NULL para h2h
    price           REAL NOT NULL,              -- cuota decimal
    captured_at     TIMESTAMPTZ NOT NULL,
    mins_to_kickoff INTEGER NOT NULL,
    window_tag      TEXT NOT NULL,              -- 't72'|'t24'|'t6'|'t1'|'close'
    source          TEXT NOT NULL DEFAULT 'the_odds_api'
);
CREATE INDEX idx_odds_match_mkt   ON odds_snapshots(match_id, market, captured_at);
CREATE INDEX idx_odds_window      ON odds_snapshots(match_id, window_tag);
CREATE INDEX idx_odds_captured    ON odds_snapshots(captured_at);

-- Control de cuota de API: qué ventanas ya se capturaron por partido
CREATE TABLE odds_capture_log (
    match_id        TEXT NOT NULL REFERENCES matches(match_id),
    window_tag      TEXT NOT NULL,
    captured_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    rows_written    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (match_id, window_tag)
);

-- ---------------------------------------------------------------------------
-- FEATURE STORE POINT-IN-TIME
-- Regla: toda feature de un partido con kickoff en T se calcula SOLO con
-- información con timestamp < as_of, y as_of <= kickoff_utc. Sin excepción.
-- ---------------------------------------------------------------------------

CREATE TABLE features_pit (
    feature_id      BIGSERIAL PRIMARY KEY,
    match_id        TEXT NOT NULL REFERENCES matches(match_id),
    as_of           TIMESTAMPTZ NOT NULL,
    fs_version      TEXT NOT NULL,              -- versión del feature set
    payload         JSONB NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (match_id, as_of, fs_version)
);
CREATE INDEX idx_features_match ON features_pit(match_id, as_of DESC);

-- Guard: as_of jamás puede ser posterior al kickoff.
CREATE OR REPLACE FUNCTION check_feature_pit() RETURNS TRIGGER AS $$
DECLARE ko TIMESTAMPTZ;
BEGIN
    SELECT kickoff_utc INTO ko FROM matches WHERE match_id = NEW.match_id;
    IF NEW.as_of > ko THEN
        RAISE EXCEPTION 'FUGA POINT-IN-TIME: as_of (%) > kickoff (%) para %',
            NEW.as_of, ko, NEW.match_id;
    END IF;
    RETURN NEW;
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_feature_pit BEFORE INSERT OR UPDATE ON features_pit
    FOR EACH ROW EXECUTE FUNCTION check_feature_pit();

-- ---------------------------------------------------------------------------
-- PREDICCIONES (INMUTABLES)
-- ---------------------------------------------------------------------------

CREATE TABLE predictions (
    prediction_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id          TEXT NOT NULL REFERENCES matches(match_id),
    model_version     TEXT NOT NULL,
    fs_version        TEXT NOT NULL,
    generated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    home_lambda       REAL NOT NULL,
    away_lambda       REAL NOT NULL,
    rho               REAL NOT NULL DEFAULT 0,
    markets           JSONB NOT NULL,           -- todos los mercados precalculados
    market_consensus  JSONB,                    -- prob. sin margen del mercado
    confidence_tier   TEXT NOT NULL DEFAULT 'medium',
    data_completeness JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX idx_pred_match ON predictions(match_id, generated_at DESC);
CREATE INDEX idx_pred_gen   ON predictions(generated_at);

-- ---------------------------------------------------------------------------
-- PICKS PUBLICADOS (INMUTABLES) - lo que vendes
-- ---------------------------------------------------------------------------

CREATE TABLE picks (
    pick_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prediction_id     UUID NOT NULL REFERENCES predictions(prediction_id),
    match_id          TEXT NOT NULL REFERENCES matches(match_id),
    market            TEXT NOT NULL,
    selection         TEXT NOT NULL,
    line              REAL,
    model_prob        REAL NOT NULL,
    advised_price     REAL NOT NULL,
    bookmaker         TEXT NOT NULL,
    edge_pct          REAL NOT NULL,            -- YA con shrinkage aplicado
    raw_edge_pct      REAL NOT NULL,            -- antes de shrinkage (auditoría)
    stake_units       REAL NOT NULL,            -- Kelly fraccional
    tier              TEXT NOT NULL DEFAULT 'free',  -- 'free' | 'paid'
    published_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    batch_id          UUID
);
CREATE INDEX idx_picks_match ON picks(match_id);
CREATE INDEX idx_picks_pub   ON picks(published_at);
CREATE INDEX idx_picks_batch ON picks(batch_id);

-- ---------------------------------------------------------------------------
-- INMUTABILIDAD REAL: bloqueo de UPDATE/DELETE a nivel de base de datos.
-- Si algún día te tienta "corregir" un pick fallido, la BD te lo impide.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION deny_mutation() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'REGISTRO INMUTABLE: % no admite % en la tabla %',
        TG_TABLE_NAME, TG_OP, TG_TABLE_NAME;
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_pred_immutable  BEFORE UPDATE OR DELETE ON predictions
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();
CREATE TRIGGER trg_picks_immutable BEFORE UPDATE OR DELETE ON picks
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();
CREATE TRIGGER trg_odds_immutable  BEFORE UPDATE OR DELETE ON odds_snapshots
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();

-- ---------------------------------------------------------------------------
-- CADENA DE HASHES - prueba criptográfica de no-revisión
-- ---------------------------------------------------------------------------

CREATE TABLE prediction_batches (
    batch_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_date      DATE NOT NULL,
    seq             BIGSERIAL,
    n_predictions   INTEGER NOT NULL,
    n_picks         INTEGER NOT NULL,
    payload_sha256  TEXT NOT NULL,              -- hash del JSON canónico
    prev_sha256     TEXT NOT NULL,              -- hash del batch anterior
    chain_sha256    TEXT NOT NULL UNIQUE,       -- sha256(prev || payload)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_ref   TEXT,                       -- URL del commit / post público
    published_at    TIMESTAMPTZ
);
CREATE INDEX idx_batches_date ON prediction_batches(batch_date);
CREATE TRIGGER trg_batches_immutable BEFORE DELETE ON prediction_batches
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();

-- ---------------------------------------------------------------------------
-- LIQUIDACIÓN Y CLV  <-- la métrica que de verdad mide si tienes edge
-- ---------------------------------------------------------------------------

CREATE TABLE pick_results (
    pick_id             UUID PRIMARY KEY REFERENCES picks(pick_id),
    closing_price       REAL,
    closing_prob_devig  REAL,
    clv_pct             REAL,                   -- (advised/closing - 1) * 100
    beat_close          BOOLEAN,
    outcome             TEXT,                   -- 'win'|'loss'|'push'|'half_win'|'half_loss'|'void'
    profit_units        REAL,
    settled_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_results_settled ON pick_results(settled_at);

-- ---------------------------------------------------------------------------
-- CALIBRACIÓN (reporte público)
-- ---------------------------------------------------------------------------

CREATE TABLE calibration_runs (
    run_id          BIGSERIAL PRIMARY KEY,
    model_version   TEXT NOT NULL,
    window_start    DATE NOT NULL,
    window_end      DATE NOT NULL,
    market          TEXT NOT NULL,
    n_obs           INTEGER NOT NULL,
    rps             REAL,
    log_loss        REAL,
    brier           REAL,
    rps_market      REAL,                       -- baseline: cierre sin margen
    bins            JSONB NOT NULL,             -- reliability diagram
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- SUSCRIPTORES (Telegram + web)
-- ---------------------------------------------------------------------------

CREATE TABLE subscribers (
    subscriber_id   BIGSERIAL PRIMARY KEY,
    telegram_id     BIGINT UNIQUE,
    email           TEXT UNIQUE,
    tier            TEXT NOT NULL DEFAULT 'free',
    status          TEXT NOT NULL DEFAULT 'active',
    valid_until     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    meta            JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE model_artifacts (
    model_version   TEXT PRIMARY KEY,
    trained_at      TIMESTAMPTZ NOT NULL,
    dataset_sha256  TEXT NOT NULL,
    params          JSONB NOT NULL,
    val_metrics     JSONB NOT NULL,
    artifact_uri    TEXT NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT FALSE,
    notes           TEXT
);

-- ---------------------------------------------------------------------------
-- VISTAS PÚBLICAS (alimentan /track-record y el dashboard)
-- ---------------------------------------------------------------------------

CREATE VIEW v_track_record AS
SELECT
    date_trunc('month', p.published_at)          AS month,
    p.tier,
    p.market,
    count(*)                                     AS n_picks,
    round(avg(r.clv_pct)::numeric, 3)            AS avg_clv_pct,
    round((avg(CASE WHEN r.beat_close THEN 1.0 ELSE 0.0 END) * 100)::numeric, 1) AS pct_beat_close,
    round(sum(r.profit_units)::numeric, 2)       AS profit_units,
    round((sum(r.profit_units) / NULLIF(sum(p.stake_units), 0) * 100)::numeric, 2) AS roi_pct
FROM picks p
JOIN pick_results r USING (pick_id)
GROUP BY 1, 2, 3
ORDER BY 1 DESC;

CREATE VIEW v_closing_odds AS
SELECT DISTINCT ON (match_id, bookmaker, market, selection, line)
    match_id, bookmaker, market, selection, line, price, captured_at
FROM odds_snapshots
ORDER BY match_id, bookmaker, market, selection, line, captured_at DESC;
