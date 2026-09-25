-- Sombra del criterio de picks "casa blanda contra precio sharp"
-- (publish/picks.py). Registra lo que el criterio HABRÍA recomendado, sin
-- publicar nada, y lo liquida contra el cierre de Pinnacle sin margen: es la
-- muestra con la que la puerta comercial decide si se reactiva la publicación.
--
-- Tablas propias y no shadow_picks (db/012): aquellas cuelgan de una
-- predicción del modelo en sombra, y este criterio no sale del modelo.

CREATE TABLE IF NOT EXISTS sharp_shadow_offers (
    offer_id           BIGSERIAL PRIMARY KEY,
    match_id           TEXT NOT NULL REFERENCES matches(match_id),
    league_id          TEXT NOT NULL,
    kickoff_utc        TIMESTAMPTZ NOT NULL,
    book               TEXT NOT NULL,
    market             TEXT NOT NULL DEFAULT 'h2h',
    selection          TEXT NOT NULL,
    price              REAL NOT NULL,
    fair_prob          REAL NOT NULL,
    raw_edge_pct       REAL NOT NULL,
    expected_edge_pct  REAL NOT NULL,
    persistence        REAL NOT NULL,   -- la usada ese día: la tabla puede cambiar
    stake_units        REAL NOT NULL,
    min_price          REAL NOT NULL,
    odds_source        TEXT NOT NULL,   -- 'api_football' | 'the_odds_api'
    odds_as_of         TIMESTAMPTZ NOT NULL,
    lead_minutes       INTEGER NOT NULL, -- kickoff - odds_as_of
    decided_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- El mismo snapshot visto en varias pasadas es UNA oferta; se conserva la
    -- primera vez que se vio (decided_at más temprano).
    UNIQUE (match_id, book, market, selection, odds_source, odds_as_of)
);
CREATE INDEX IF NOT EXISTS idx_sharp_shadow_match ON sharp_shadow_offers(match_id);

DROP TRIGGER IF EXISTS trg_sharp_shadow_immutable ON sharp_shadow_offers;
CREATE TRIGGER trg_sharp_shadow_immutable
    BEFORE UPDATE OR DELETE ON sharp_shadow_offers
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();

CREATE TABLE IF NOT EXISTS sharp_shadow_results (
    offer_id            BIGINT PRIMARY KEY REFERENCES sharp_shadow_offers(offer_id),
    closing_price       REAL,       -- Pinnacle al cierre, con margen
    closing_prob_devig  REAL,       -- Pinnacle al cierre, sin margen
    clv_pct             REAL,
    ev_close_pct        REAL,       -- lo que decide la puerta
    beat_close          BOOLEAN,
    outcome             TEXT NOT NULL,
    profit_units        REAL NOT NULL,  -- a 1 unidad, para comparar ofertas
    settled_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
