-- ============================================================================
-- 045 - Reto escalera (pedido del usuario, 2026-10-08)
--
-- Un reto encadena escalones: todo el saldo va al siguiente pronóstico y el
-- reto acaba al ganar `pasos_objetivo` escalones (3 a 6) o al perder uno.
-- Puede haber varios retos abiertos a la vez. Las reglas
-- y su justificación están en `src/qf/publish/escalera.py`.
--
-- Las tres tablas son inmutables, como `picks`: el estado de un reto (en
-- curso, completado, fallido, saldo, retirada) se DERIVA de sus filas y no se
-- guarda en ningún sitio que se pueda corregir después.
-- ============================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS escalera_retos (
    reto_id         BIGSERIAL PRIMARY KEY,
    stake_inicial   NUMERIC(10, 2) NOT NULL CHECK (stake_inicial > 0),
    pasos_objetivo  SMALLINT NOT NULL CHECK (pasos_objetivo BETWEEN 1 AND 20),
    cuota_min       REAL NOT NULL,
    cuota_max       REAL NOT NULL CHECK (cuota_max >= cuota_min),
    ev_min          REAL NOT NULL,          -- cuota × prob − 1 mínimo por escalón
    freeroll_x      REAL,                   -- se retira la inversión al llegar a este múltiplo
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS escalera_pasos (
    paso_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reto_id      BIGINT NOT NULL REFERENCES escalera_retos(reto_id),
    paso         SMALLINT NOT NULL CHECK (paso >= 1),
    match_id     TEXT NOT NULL REFERENCES matches(match_id),
    market       TEXT NOT NULL CHECK (market IN ('h2h', 'totals', 'team_totals_home',
                                                 'team_totals_away', 'spreads')),
    selection    TEXT NOT NULL,
    line         REAL,                      -- hándicap: el del lado elegido (+1,5 = recibe 1,5)
    prob         DOUBLE PRECISION NOT NULL CHECK (prob > 0 AND prob < 1),  -- Pinnacle sin margen
    fair_price   REAL NOT NULL,             -- 1 / prob
    price        REAL NOT NULL CHECK (price > 1),   -- mejor cuota de SOFT_BOOKS: a la que sube el saldo
    book         TEXT NOT NULL,
    odds_source  TEXT NOT NULL,
    odds_as_of   TIMESTAMPTZ NOT NULL,
    decided_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (reto_id, paso)
);
CREATE INDEX IF NOT EXISTS idx_escalera_pasos_decided ON escalera_pasos(decided_at);

CREATE TABLE IF NOT EXISTS escalera_resultados (
    paso_id     UUID PRIMARY KEY REFERENCES escalera_pasos(paso_id),
    -- 'void': partido aplazado. 'push': hándicap entero devuelto. En los dos
    -- el escalón no cuenta y el saldo no cambia.
    outcome     TEXT NOT NULL CHECK (outcome IN ('win', 'loss', 'push', 'void')),
    home_goals  SMALLINT,
    away_goals  SMALLINT,
    settled_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK ((outcome = 'void') = (home_goals IS NULL))
);

DROP TRIGGER IF EXISTS trg_escalera_retos_immutable ON escalera_retos;
CREATE TRIGGER trg_escalera_retos_immutable BEFORE UPDATE OR DELETE ON escalera_retos
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();
DROP TRIGGER IF EXISTS trg_escalera_pasos_immutable ON escalera_pasos;
CREATE TRIGGER trg_escalera_pasos_immutable BEFORE UPDATE OR DELETE ON escalera_pasos
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();
DROP TRIGGER IF EXISTS trg_escalera_resultados_immutable ON escalera_resultados;
CREATE TRIGGER trg_escalera_resultados_immutable BEFORE UPDATE OR DELETE ON escalera_resultados
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qf_readonly') THEN
    GRANT SELECT ON escalera_retos, escalera_pasos, escalera_resultados TO qf_readonly;
  END IF;
END $$;

COMMIT;
