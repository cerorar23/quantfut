-- ============================================================================
-- 098 - Parley v2.1: lote propio, sellado inmutable y patas de cualquier deporte
-- (pedido del usuario, 2026-11-06; diseño en harness/tareas.md, fases 3 y 4)
--
-- El parley v2 se elige DESPUÉS del lote diario (predecir -> sellar -> seleccionar ->
-- sellar): tiene su propia cadena de hashes, que no toca `prediction_batches` ni
-- `seal()`. Cada lote guarda el hash del lote diario que lo precede como prueba del
-- orden. Las patas no apuntan a `matches`: el evento puede ser de fútbol, tenis o NBA.
-- Todo es inmutable como `parley_*` (db/053).
--
-- OJO: la numeración puede chocar con migraciones de otras ramas; comprobar antes de aplicar.
-- ============================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS parley_v2_lotes (
    lote_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dia                 DATE NOT NULL,
    estrategia          TEXT NOT NULL,
    version             TEXT NOT NULL,
    clave               TEXT NOT NULL UNIQUE,             -- idempotencia: estrategia + versión + día (+ partido)
    ambito              TEXT NOT NULL DEFAULT 'diario' CHECK (ambito IN ('diario', 'partido')),
    evento_id           TEXT,                              -- solo ambito 'partido' (NBA)
    decidido_at         TIMESTAMPTZ NOT NULL,
    barrera             JSONB NOT NULL,                    -- recibos y versiones que se comprobaron
    lote_diario_sha256  TEXT,                              -- cadena del lote diario que lo precede
    payload_sha256      TEXT NOT NULL,
    prev_sha256         TEXT NOT NULL,
    chain_sha256        TEXT NOT NULL UNIQUE,
    sellado_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_parley_v2_lotes_dia ON parley_v2_lotes(dia);

CREATE TABLE IF NOT EXISTS parley_v2_tickets (
    ticket_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lote_id      UUID NOT NULL REFERENCES parley_v2_lotes(lote_id),
    target       REAL NOT NULL,
    tipo         TEXT NOT NULL CHECK (tipo IN ('multievento', 'same_game')),
    estado       TEXT NOT NULL CHECK (estado IN ('publicado', 'solo_referencia')),
    n_patas      SMALLINT NOT NULL CHECK (n_patas BETWEEN 2 AND 6),
    cuota_total  REAL NOT NULL CHECK (cuota_total > 1),
    prob_conjunta  DOUBLE PRECISION,                       -- NULL en un same-game sin modelo conjunto
    prob_prudente  DOUBLE PRECISION,
    p_bajo       DOUBLE PRECISION,
    p_alto       DOUBLE PRECISION,
    motivos      JSONB NOT NULL DEFAULT '[]',
    UNIQUE (lote_id, target)
);

CREATE TABLE IF NOT EXISTS parley_v2_patas (
    pata_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id    UUID NOT NULL REFERENCES parley_v2_tickets(ticket_id),
    deporte      TEXT NOT NULL CHECK (deporte IN ('futbol', 'tenis', 'nba')),
    evento_id    TEXT NOT NULL,                            -- match_id de fútbol o id del evento en PropLine
    mercado      TEXT NOT NULL,
    seleccion    TEXT NOT NULL,
    linea        REAL,
    jugador_id   TEXT,
    jugador      TEXT,
    prob         DOUBLE PRECISION NOT NULL CHECK (prob > 0 AND prob < 1),
    price        REAL NOT NULL CHECK (price > 1),
    book         TEXT NOT NULL,
    odds_source  TEXT NOT NULL,
    odds_as_of   TIMESTAMPTZ NOT NULL,                     -- hora de la cuota: nunca posterior a la decisión
    inicio_utc   TIMESTAMPTZ NOT NULL,                     -- hora del evento al decidir
    n_casas_ref  SMALLINT,
    referencia   TEXT,
    evento       JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_parley_v2_patas_evento ON parley_v2_patas(deporte, evento_id);

CREATE TABLE IF NOT EXISTS parley_v2_resultados_pata (
    pata_id     UUID PRIMARY KEY REFERENCES parley_v2_patas(pata_id),
    outcome     TEXT NOT NULL CHECK (outcome IN ('win', 'loss', 'push', 'void')),
    valor       DOUBLE PRECISION,
    fuente      TEXT NOT NULL,
    settled_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS parley_v2_resultados (
    ticket_id      UUID PRIMARY KEY REFERENCES parley_v2_tickets(ticket_id),
    outcome        TEXT NOT NULL CHECK (outcome IN ('ganado', 'perdido', 'nulo')),
    factor_pago    REAL NOT NULL CHECK (factor_pago >= 0),
    settled_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY['parley_v2_lotes', 'parley_v2_tickets', 'parley_v2_patas',
                           'parley_v2_resultados_pata', 'parley_v2_resultados'] LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_immutable ON %s', t, t);
    EXECUTE format('CREATE TRIGGER trg_%s_immutable BEFORE UPDATE OR DELETE ON %s '
                   'FOR EACH ROW EXECUTE FUNCTION deny_mutation()', t, t);
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qf_readonly') THEN
      EXECUTE format('GRANT SELECT ON %s TO qf_readonly', t);
    END IF;
  END LOOP;
END $$;

COMMIT;
