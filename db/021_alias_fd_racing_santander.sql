-- ============================================================================
-- 021 - Alias de football-data para Racing Santander (LaLiga 2026/27)
--
-- Racing lo dio de alta API-Football ('Racing Santander') al ascender;
-- football-data.co.uk lo llama 'Santander'. Sin alias, la carga de la
-- temporada 2026/27 (history_fd) lo registraría como club NUEVO: el mismo
-- equipo dos veces, con la historia partida y sus partidos duplicados porque
-- la guarda anti-duplicados compara por team_id. Mismo club y misma liga:
-- ALIAS. El difuso daba 72, por debajo del umbral (ver 013).
-- ============================================================================
INSERT INTO team_aliases (alias, source, team_id)
SELECT 'Santander', 'football_data', t.team_id
FROM teams t
WHERE t.league_id = 'es.laliga' AND t.canonical_name = 'Racing Santander'
ON CONFLICT (alias, source) DO UPDATE SET team_id = EXCLUDED.team_id;

UPDATE unresolved_names SET resolved = TRUE
WHERE raw_name = 'Santander' AND source = 'football_data'
  AND EXISTS (SELECT 1 FROM team_aliases
              WHERE alias = 'Santander' AND source = 'football_data');
