-- ============================================================================
-- 046 - Escalera por probabilidad: córners, tarjetas amarillas, goles y ambos
-- anotan (decisión del usuario, 2026-10-08).
--
-- matches: amarillas de cada equipo y árbitro. Se llenan desde football-data
-- (ligas principales; el árbitro solo lo trae la Premier) y, desde ahora, con
-- la respuesta de API-Football que `results` y `fixtures` ya piden. Los córners
-- ya existían (home_corners / away_corners, db/001).
--
-- escalera_pasos: mercados nuevos. El CHECK de 045 se declaró en la columna:
-- PostgreSQL lo llamó escalera_pasos_market_check. La guardia aborta si queda
-- otro CHECK sobre `market`.
-- ============================================================================
BEGIN;

ALTER TABLE matches ADD COLUMN IF NOT EXISTS home_yellow SMALLINT;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS away_yellow SMALLINT;
-- Rojas: el mercado "tarjetas" de la escalera cuenta amarillas + rojas, una
-- por tarjeta (las casas difieren en cómo cuentan la roja; se dice en la web).
ALTER TABLE matches ADD COLUMN IF NOT EXISTS home_red SMALLINT;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS away_red SMALLINT;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS referee TEXT;
CREATE INDEX IF NOT EXISTS idx_matches_referee ON matches(referee) WHERE referee IS NOT NULL;

ALTER TABLE escalera_pasos DROP CONSTRAINT IF EXISTS escalera_pasos_market_check;
ALTER TABLE escalera_pasos ADD CONSTRAINT escalera_pasos_market_check
    CHECK (market IN ('h2h', 'totals', 'team_totals_home', 'team_totals_away', 'spreads',
                      'btts', 'corners', 'cards'));

-- Regla del 2026-10-08: sin filtro de valor. NULL en ev_min = sin mínimo.
ALTER TABLE escalera_retos ALTER COLUMN ev_min DROP NOT NULL;
COMMENT ON COLUMN escalera_retos.ev_min IS
    'Valor esperado mínimo por escalón (cuota × prob − 1). NULL = sin filtro: se elige el más probable.';

-- En córners y tarjetas el marcador no basta para liquidar: se guarda el total.
ALTER TABLE escalera_resultados ADD COLUMN IF NOT EXISTS valor SMALLINT;
COMMENT ON COLUMN escalera_resultados.valor IS
    'Córners o tarjetas (amarillas + rojas) totales del partido (mercados corners / cards). NULL en el resto.';

DO $$ BEGIN
  IF (SELECT count(*) FROM pg_constraint
      WHERE conrelid = 'escalera_pasos'::regclass AND contype = 'c'
        AND pg_get_constraintdef(oid) LIKE '%market%') <> 1 THEN
    RAISE EXCEPTION 'escalera_pasos tiene más de un CHECK sobre market: revisar db/046';
  END IF;
END $$;

COMMIT;
