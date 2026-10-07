-- ============================================================================
-- 042 - "Marca el local / el visitante" en la línea de alta probabilidad
-- (decisión del usuario, 2026-10-07). Amplía el CHECK de mercados de 040.
-- El CHECK de 040 se declaró en la columna: PostgreSQL lo llamó
-- alta_prob_picks_market_check (visto en producción el 2026-10-06). La
-- guardia aborta si queda otro CHECK sobre `market` (p. ej. un nombre
-- distinto): con dos CHECK, los mercados nuevos fallarían al insertar.
-- ============================================================================
BEGIN;

ALTER TABLE alta_prob_picks DROP CONSTRAINT IF EXISTS alta_prob_picks_market_check;
ALTER TABLE alta_prob_picks ADD CONSTRAINT alta_prob_picks_market_check
    CHECK (market IN ('h2h', 'double_chance', 'totals',
                      'team_totals_home', 'team_totals_away'));

-- Con el mercado de equipo, `line` ya no es solo la línea de goles del partido.
COMMENT ON COLUMN af_odds_snapshots.line IS
    'Línea de goles: totals (1.5, 2.75...) o goles de un equipo (team_totals_home/away, 0.5). NULL en h2h.';
COMMENT ON COLUMN alta_prob_picks.line IS
    'Línea de goles: totals (1,5 / 3,5) o de un equipo (0,5). NULL en 1X2 y doble oportunidad.';

DO $$ BEGIN
  IF (SELECT count(*) FROM pg_constraint
      WHERE conrelid = 'alta_prob_picks'::regclass AND contype = 'c'
        AND pg_get_constraintdef(oid) LIKE '%market%') <> 1 THEN
    RAISE EXCEPTION 'alta_prob_picks tiene más de un CHECK sobre market: revisar db/042';
  END IF;
END $$;

COMMIT;
