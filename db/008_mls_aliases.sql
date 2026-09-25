-- ============================================================================
-- 008 - Alias de FBref para la MLS
--
-- Mismo problema que en 005 y misma solución: revisados a mano, uno por uno.
-- La MLS es el caso más hostil de las 8 ligas porque FBref alterna entre el
-- nombre corto y el largo DENTRO DEL MISMO FICHERO según la temporada
-- ('Seattle' y 'Seattle Sounders FC', 'San Jose' y 'SJ Earthquakes'), así que
-- hay varios alias apuntando al mismo equipo. Eso es correcto: la tabla
-- team_aliases tiene clave (alias, source), no (team_id, source).
--
-- POR QUÉ NO SE PUEDE DEJAR AL EMPAREJADOR DIFUSO
-- ------------------------------------------------
-- 'LAFC' y 'LA Galaxy' comparten prefijo y son dos clubes distintos de la
-- misma ciudad. 'St. Louis' contra 'St. Louis City' se queda en 84 puntos,
-- por debajo del umbral de 90. Bajar el umbral para capturarlos haría que
-- 'LAFC' pudiera caer en 'Los Angeles Galaxy', que es exactamente el error
-- que parte el historial de dos equipos a la vez y no da ningún aviso.
--
-- NOTA SOBRE MONTREAL: 'Montreal Impact' es el nombre anterior del club que
-- hoy es 'CF Montréal'. Es la MISMA franquicia, así que apuntan al mismo
-- team_id a propósito: separarlos partiría en dos un historial continuo.
--
-- Requiere que la ingesta de football-data haya creado ya los equipos de
-- us.mls (src/qf/ingest/history_fd.py).
-- ============================================================================

DO $$
DECLARE n INTEGER;
BEGIN
  SELECT count(*) INTO n FROM teams WHERE league_id = 'us.mls';
  IF n = 0 THEN
    RAISE WARNING 'No hay equipos en us.mls. Corre la ingesta histórica antes '
                  'que este fichero o no se insertará ningún alias.';
  END IF;
END $$;

INSERT INTO team_aliases (alias, source, team_id)
SELECT v.alias, 'fbref', t.team_id
FROM (VALUES
  ('D.C. United',       'DC United'),
  ('Dynamo',            'Houston Dynamo'),
  ('Dynamo FC',         'Houston Dynamo'),
  ('LA Galaxy',         'Los Angeles Galaxy'),
  ('LAFC',              'Los Angeles FC'),
  ('Montreal Impact',   'CF Montreal'),
  ('NE Revolution',     'New England Revolution'),
  ('New England',       'New England Revolution'),
  ('NY Red Bulls',      'New York Red Bulls'),
  ('NYCFC',             'New York City'),
  ('Philadelphia',      'Philadelphia Union'),
  ('SJ Earthquakes',    'San Jose Earthquakes'),
  ('San Jose',          'San Jose Earthquakes'),
  ('Seattle',           'Seattle Sounders'),
  ('Sporting KC',       'Sporting Kansas City'),
  ('St. Louis',         'St. Louis City'),
  ('Vancouver',         'Vancouver Whitecaps'),
  ('Vancouver W''caps', 'Vancouver Whitecaps')
) AS v(alias, canonical)
JOIN teams t ON t.league_id = 'us.mls' AND t.canonical_name = v.canonical
ON CONFLICT (alias, source) DO UPDATE SET team_id = EXCLUDED.team_id;
