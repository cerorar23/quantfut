-- ============================================================================
-- 049 - Historial de football-data para las ligas "solo sharp"
-- (pedido del usuario, 2026-10-11: activarlas en el modelo propio).
--
-- Solo el catálogo: dice de qué CSV sale cada liga. No carga nada ni toca
-- `model_enabled`; la carga va por `python -m qf.ingest.history_fd cargar`
-- después de un ensayo en seco (`... ensayo`) sin dudosos.
--
-- Principal (un CSV por temporada, con cierre de Pinnacle, tiros, córners y
-- tarjetas): E1, SP2, D2, I2, F2, T1. Extra (un CSV con todo, solo
-- resultado y cuotas): NOR, SWE, DNK, SWZ. Ni Chile ni la Série B de Brasil
-- están en football-data: `new/CHL.csv` REDIRIGE a `new/CHN.csv` (Superliga
-- china) con un 200, y el ensayo del 2026-10-11 lo cazó proponiendo 44 equipos
-- nuevos chinos para la Primera chilena. Chile queda explícitamente sin código.
-- ============================================================================
BEGIN;

UPDATE leagues SET fd_code = NULL, fd_extra = FALSE WHERE league_id = 'cl.primera';

UPDATE leagues SET fd_code = v.code, fd_extra = v.extra
FROM (VALUES
    ('gb.championship', 'E1',  FALSE),
    ('es.laliga2',      'SP2', FALSE),
    ('de.bundesliga2',  'D2',  FALSE),
    ('it.serie_b',      'I2',  FALSE),
    ('fr.ligue_2',      'F2',  FALSE),
    ('tr.super_lig',    'T1',  FALSE),
    ('no.eliteserien',  'NOR', TRUE),
    ('se.allsvenskan',  'SWE', TRUE),
    ('dk.superliga',    'DNK', TRUE),
    ('ch.super_league', 'SWZ', TRUE)
) AS v(league_id, code, extra)
WHERE leagues.league_id = v.league_id;

DO $$ BEGIN
  IF (SELECT count(*) FROM leagues
      WHERE league_id IN ('gb.championship', 'es.laliga2', 'de.bundesliga2', 'it.serie_b',
                          'fr.ligue_2', 'tr.super_lig', 'no.eliteserien', 'se.allsvenskan',
                          'dk.superliga', 'ch.super_league')
        AND fd_code IS NOT NULL) <> 10 THEN
    RAISE EXCEPTION 'db/049: no están las 10 ligas en el catálogo';
  END IF;
END $$;

COMMIT;
