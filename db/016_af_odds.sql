-- Cuotas 1X2 de API-Football: Bet365, Betano, 1xBet y William Hill junto a
-- Pinnacle en la MISMA respuesta. Son las casas donde apuestan los
-- suscriptores y The Odds API no tiene ni Bet365 ni Betano.
--
-- TABLA SEPARADA de odds_snapshots, a propósito. Esa tabla la leen sin filtrar
-- por casa el consenso de mercado de las predicciones, el mejor precio de
-- picks, /fair-price, la sombra y el chequeo de salud. API-Football actualiza
-- cada liga de golpe cada varias horas (medido el 2026-09-23: 2 h en MLS, 19 h
-- en Liga MX, 3,5 días en Premier en parón): mezclarlas metería precios
-- viejos en todo eso, y el chequeo de salud ("última captura") daría por vivo
-- un worker de The Odds API caído.
--
-- Dos tiempos por fila:
--   provider_updated_at  cuándo tenía la casa ese precio ('update' del proveedor)
--   fetched_at           cuándo lo supimos
-- Una decisión tomada en T solo puede usar filas con fetched_at <= T.

CREATE TABLE IF NOT EXISTS af_odds_snapshots (
    snapshot_id          BIGSERIAL PRIMARY KEY,
    match_id             TEXT NOT NULL REFERENCES matches(match_id),
    af_fixture_id        INTEGER NOT NULL,
    bookmaker            TEXT NOT NULL,      -- 'bet365', 'pinnacle', '1xbet'...
    market               TEXT NOT NULL,      -- 'h2h'
    selection            TEXT NOT NULL,      -- 'home' | 'draw' | 'away'
    price                REAL NOT NULL,
    provider_updated_at  TIMESTAMPTZ NOT NULL,
    fetched_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    mins_to_kickoff      INTEGER NOT NULL,   -- desde provider_updated_at
    UNIQUE (match_id, bookmaker, market, selection, provider_updated_at)
);
CREATE INDEX IF NOT EXISTS idx_af_odds_match ON af_odds_snapshots(match_id, provider_updated_at);
CREATE INDEX IF NOT EXISTS idx_af_odds_fetched ON af_odds_snapshots(fetched_at);

DROP TRIGGER IF EXISTS trg_af_odds_immutable ON af_odds_snapshots;
CREATE TRIGGER trg_af_odds_immutable
    BEFORE UPDATE OR DELETE ON af_odds_snapshots
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();
