-- ============================================================================
-- 007 - MLS, Champions League y Europa League
--
-- Hasta aquí "liga" y "competición" eran lo mismo: todos los partidos de una
-- liga los jugaban equipos de esa liga. Las copas europeas rompen ese
-- supuesto, y romperlo mal es caro:
--
--   Si se dieran de alta equipos nuevos bajo league_id='eu.ucl', el Real
--   Madrid de Champions sería un equipo DISTINTO del Real Madrid de LaLiga,
--   con 6-13 partidos de historia y ningún rival en común. El modelo de
--   fuerza no aprendería nada y encima ensuciaría el catálogo con duplicados.
--
-- La decisión es separar los dos conceptos sin tocar el esquema existente:
--
--   matches.league_id -> la COMPETICIÓN en la que se juega el partido.
--   teams.league_id   -> la liga DOMÉSTICA a la que pertenece el equipo.
--
-- No hay ninguna restricción que obligue a que coincidan, así que un partido
-- de 'eu.ucl' apunta a equipos cuyo teams.league_id sigue siendo 'es.laliga'
-- o 'gb.premier_league'. La ingesta de copas NUNCA crea equipos: si no
-- reconoce a los dos, descarta el partido.
--
-- La columna `cross_league` marca esas competiciones para que el resto del
-- sistema sepa que ahí los equipos vienen de fuera.
-- ============================================================================

ALTER TABLE leagues
  ADD COLUMN IF NOT EXISTS cross_league BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN leagues.cross_league IS
  'TRUE en competiciones donde los equipos pertenecen a otras ligas (copas '
  'europeas). En ellas teams.league_id != matches.league_id y la ingesta no '
  'da de alta equipos nuevos.';

-- Identificador del dataset de worldfootballR_data. Solo lo usan las copas:
-- su histórico no existe en CSV, únicamente como .rds (ver ingest/uefa_cups.py).
ALTER TABLE leagues
  ADD COLUMN IF NOT EXISTS rds_asset TEXT;

INSERT INTO leagues (league_id, country, name, tier, fd_code, fd_extra,
                     odds_api_key, cross_league, rds_asset) VALUES
  -- MLS: liga doméstica normal. football-data.co.uk la publica en el formato
  -- "extra" (new/USA.csv), temporada de año natural como Brasil, y con cuotas
  -- de cierre de Pinnacle desde 2012.
  ('us.mls', 'USA', 'Major League Soccer', 1, 'USA', TRUE,
   'soccer_usa_mls', FALSE, NULL),

  -- Copas europeas. fd_code NULL a propósito: football-data.co.uk solo cubre
  -- ligas domésticas, así que aquí no hay cuotas históricas gratuitas de
  -- ninguna clase. Entran como datos de ENTRENAMIENTO (resultado + xG), no
  -- como mercado apostable, hasta que odds_worker acumule cierres propios.
  ('eu.ucl', 'Europe', 'UEFA Champions League', 1, NULL, FALSE,
   'soccer_uefa_champs_league', TRUE, 'uefa_champions_league_match_results.rds'),
  ('eu.uel', 'Europe', 'UEFA Europa League',    1, NULL, FALSE,
   'soccer_uefa_europa_league', TRUE, 'uefa_europa_league_match_results.rds')
ON CONFLICT (league_id) DO UPDATE
  SET odds_api_key = EXCLUDED.odds_api_key,
      cross_league = EXCLUDED.cross_league,
      rds_asset    = EXCLUDED.rds_asset;

-- IDs de API-Football. SIN VERIFICAR contra la API: no hay clave configurada
-- todavía. Córrelo con scripts/verify_league_ids.py antes de fiarte, igual que
-- avisa db/003. Un id equivocado no da error: devuelve 0 partidos y el
-- calendario de esa competición se queda vacío en silencio.
UPDATE leagues SET api_football_id = 253, season_style = 'calendar'
  WHERE league_id = 'us.mls';
UPDATE leagues SET api_football_id = 2,   season_style = 'european'
  WHERE league_id = 'eu.ucl';
UPDATE leagues SET api_football_id = 3,   season_style = 'european'
  WHERE league_id = 'eu.uel';
