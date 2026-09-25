-- ============================================================================
-- 027 - Alias de The Odds API para Racing Santander (LaLiga 2026/27)
--
-- The Odds API lo llama 'Real Racing Club de Santander'; el club lo dio de
-- alta API-Football ('Racing Santander') al ascender. Sin alias, sus partidos
-- de LaLiga no reciben cuotas de The Odds API ni cierre de Pinnacle. Revisión
-- del 2026-09-25: comprobados los 305 equipos de las 13 ligas domésticas en la
-- lista de partidos de The Odds API (gratuita); este era el ÚNICO sin
-- resolver. Mismo club y misma liga: ALIAS, nunca equipo nuevo.
-- ============================================================================
INSERT INTO team_aliases (alias, source, team_id)
SELECT 'Real Racing Club de Santander', 'odds_api', t.team_id
FROM teams t
WHERE t.league_id = 'es.laliga' AND t.canonical_name = 'Racing Santander'
ON CONFLICT (alias, source) DO NOTHING;

UPDATE unresolved_names SET resolved = TRUE
WHERE raw_name = 'Real Racing Club de Santander' AND source = 'odds_api'
  AND EXISTS (SELECT 1 FROM team_aliases
              WHERE alias = 'Real Racing Club de Santander' AND source = 'odds_api');
