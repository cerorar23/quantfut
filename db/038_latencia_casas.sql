-- ============================================================================
-- 038 - Latencia de las casas blandas (idea 3 de la literatura, 2026-10-03)
--
-- The Odds API da, por casa y mercado, la hora de su último cambio
-- (`last_update`). Hasta hoy se descartaba. Sin ella no se puede saber si una
-- oferta existe porque la casa blanda aún no reaccionó a Pinnacle, ni cuánto
-- tarda en hacerlo.
--
-- 3A: `odds_snapshots.book_updated_at`. Nullable: las filas anteriores y las
-- de football-data no la tienen. Es ADD COLUMN: los triggers de inmutabilidad
-- (UPDATE/DELETE) no se tocan y ninguna fila existente se reescribe.
--
-- 3B: `odds_rafagas`, tabla APARTE. Capturas cada 5 min en las 6 h previas,
-- solo 1X2. Fuera de `odds_snapshots` a propósito: las ventanas, la sombra y
-- el cierre no deben verlas. Una fila por CAMBIO de precio (clave con
-- `book_updated_at`); `rafagas_log` guarda cada consulta, que es lo que dice
-- hasta cuándo seguía vigente un precio, y los créditos gastados para el tope.
-- ============================================================================
BEGIN;

ALTER TABLE odds_snapshots ADD COLUMN IF NOT EXISTS book_updated_at TIMESTAMPTZ;
COMMENT ON COLUMN odds_snapshots.book_updated_at IS
  'last_update de The Odds API para esa casa y mercado: cuándo cambió su '
  'precio por última vez. NULL en filas anteriores al 2026-10-03 y en otras '
  'fuentes.';

CREATE TABLE IF NOT EXISTS odds_rafagas (
    match_id         TEXT NOT NULL REFERENCES matches(match_id),
    bookmaker        TEXT NOT NULL,
    selection        TEXT NOT NULL CHECK (selection IN ('home', 'draw', 'away')),
    price            REAL NOT NULL,
    book_updated_at  TIMESTAMPTZ NOT NULL,
    first_seen_at    TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (match_id, bookmaker, selection, book_updated_at)
);

CREATE TABLE IF NOT EXISTS rafagas_log (
    sport_key    TEXT NOT NULL,
    captured_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    credits      INTEGER NOT NULL,
    match_ids    TEXT[] NOT NULL,
    PRIMARY KEY (sport_key, captured_at)
);

DROP TRIGGER IF EXISTS trg_odds_rafagas_immutable ON odds_rafagas;
CREATE TRIGGER trg_odds_rafagas_immutable
    BEFORE UPDATE OR DELETE ON odds_rafagas
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qf_readonly') THEN
    GRANT SELECT ON odds_rafagas, rafagas_log TO qf_readonly;
  END IF;
END $$;

COMMIT;
