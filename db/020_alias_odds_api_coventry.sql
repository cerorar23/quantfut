-- ============================================================================
-- 020 - Alias de The Odds API para Coventry (Premier League 2026/27)
--
-- Coventry lo dio de alta API-Football ('Coventry') al ascender; The Odds API
-- lo llama 'Coventry City'. Sin alias, odds_worker descartaba sus eventos de
-- la Premier: 8 descartes entre el 22 y el 24-sep, cuotas que no se recuperan.
-- Mismo club y misma liga: ALIAS, nunca equipo nuevo. El difuso daba 76, por
-- debajo del umbral, y no hay que bajarlo (ver 013).
--
-- El resto de pendientes de ese momento (Galatasaray, Celtic, Rangers, Club
-- Brugge…) son clubes de ligas fuera del catálogo que juegan copas europeas:
-- irresolubles por diseño. No se dan de alta.
-- ============================================================================
INSERT INTO team_aliases (alias, source, team_id)
SELECT 'Coventry City', 'odds_api', t.team_id
FROM teams t
WHERE t.league_id = 'gb.premier_league' AND t.canonical_name = 'Coventry'
ON CONFLICT (alias, source) DO UPDATE SET team_id = EXCLUDED.team_id;

UPDATE unresolved_names SET resolved = TRUE
WHERE raw_name = 'Coventry City' AND source = 'odds_api'
  AND EXISTS (SELECT 1 FROM team_aliases
              WHERE alias = 'Coventry City' AND source = 'odds_api');
