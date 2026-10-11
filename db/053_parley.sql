-- ============================================================================
-- 053 - Parley del día (pedido del usuario, 2026-10-11)
--
-- Cada día, 1 a 5 parlays de cuota 1,90-5,00, uno por escalón, el más probable
-- de cada uno. Reglas en `src/qf/publish/parley.py`; diseño en
-- docs/superpowers/specs/2026-10-11-parley-design.md.
--
-- Inmutables como `escalera_*`: el resultado se DERIVA de filas que no se
-- pueden corregir después. Se sellan en el lote del día (hashchain).
-- ============================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS parley_tickets (
    ticket_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dia          DATE NOT NULL,
    escalon      SMALLINT NOT NULL CHECK (escalon BETWEEN 1 AND 5),
    cuota_total  REAL NOT NULL CHECK (cuota_total > 1),
    prob_total   DOUBLE PRECISION NOT NULL CHECK (prob_total > 0 AND prob_total < 1),
    n_patas      SMALLINT NOT NULL CHECK (n_patas BETWEEN 2 AND 6),
    decided_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (dia, escalon)
);
CREATE INDEX IF NOT EXISTS idx_parley_tickets_decided ON parley_tickets(decided_at);

CREATE TABLE IF NOT EXISTS parley_patas (
    pata_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id    UUID NOT NULL REFERENCES parley_tickets(ticket_id),
    match_id     TEXT NOT NULL REFERENCES matches(match_id),
    market       TEXT NOT NULL CHECK (market IN ('h2h', 'totals', 'team_totals_home',
                                                 'team_totals_away', 'spreads', 'btts',
                                                 'corners', 'cards', 'corners_home',
                                                 'corners_away')),
    selection    TEXT NOT NULL,
    line         REAL,
    prob         DOUBLE PRECISION NOT NULL CHECK (prob > 0 AND prob < 1),
    fair_price   REAL NOT NULL,
    price        REAL NOT NULL CHECK (price > 1),
    book         TEXT NOT NULL,
    odds_source  TEXT NOT NULL,
    odds_as_of   TIMESTAMPTZ NOT NULL,
    UNIQUE (ticket_id, match_id)
);
CREATE INDEX IF NOT EXISTS idx_parley_patas_match ON parley_patas(match_id);

CREATE TABLE IF NOT EXISTS parley_resultados_pata (
    pata_id     UUID PRIMARY KEY REFERENCES parley_patas(pata_id),
    -- 'push': hándicap entero devuelto; 'void': aplazado o sin estadísticas.
    outcome     TEXT NOT NULL CHECK (outcome IN ('win', 'loss', 'push', 'void')),
    home_goals  SMALLINT,
    away_goals  SMALLINT,
    valor       SMALLINT,               -- córners o tarjetas con que se liquidó
    settled_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS parley_resultados (
    ticket_id      UUID PRIMARY KEY REFERENCES parley_tickets(ticket_id),
    outcome        TEXT NOT NULL CHECK (outcome IN ('ganado', 'perdido', 'nulo')),
    factor_pago    REAL NOT NULL CHECK (factor_pago >= 0),
    -- Producto de las patas que contaron (ganadas o perdidas): lo prometido
    -- con lo que de verdad se jugó.
    prob_efectiva  DOUBLE PRECISION NOT NULL,
    settled_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_parley_tickets_immutable ON parley_tickets;
CREATE TRIGGER trg_parley_tickets_immutable BEFORE UPDATE OR DELETE ON parley_tickets
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();
DROP TRIGGER IF EXISTS trg_parley_patas_immutable ON parley_patas;
CREATE TRIGGER trg_parley_patas_immutable BEFORE UPDATE OR DELETE ON parley_patas
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();
DROP TRIGGER IF EXISTS trg_parley_resultados_pata_immutable ON parley_resultados_pata;
CREATE TRIGGER trg_parley_resultados_pata_immutable BEFORE UPDATE OR DELETE ON parley_resultados_pata
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();
DROP TRIGGER IF EXISTS trg_parley_resultados_immutable ON parley_resultados;
CREATE TRIGGER trg_parley_resultados_immutable BEFORE UPDATE OR DELETE ON parley_resultados
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qf_readonly') THEN
    GRANT SELECT ON parley_tickets, parley_patas, parley_resultados_pata,
                    parley_resultados TO qf_readonly;
  END IF;
END $$;

COMMIT;
