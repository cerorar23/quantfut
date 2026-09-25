-- ============================================================================
-- 011 - Alias de FBref para Bundesliga, Ligue 1 y Primeira Liga
--
-- Mismo criterio que 005, 008 y 009: revisados uno a uno. Aquí el patrón
-- dominante es que FBref conserva el nombre completo del club y
-- football-data.co.uk lo abrevia, o al revés.
--
-- LOS TRES QUE NO SE PUEDEN DEJAR AL EMPAREJADOR DIFUSO
-- ------------------------------------------------------
--   'Paris S-G' se queda en 82 puntos contra 'Paris SG' y NO resuelve. Bajar
--   el umbral para capturarlo lo pondría a tiro de 'Paris FC', que es otro
--   club de la misma ciudad y que también está en el catálogo.
--
--   'Vitória' a secas es Vitória de Guimarães, no Vitória de Setúbal. Se
--   comprobó por fechas: 'Vitória' aparece de forma continua de 2018 a 2025,
--   mientras que FBref llama 'Vitória Setúbal' al otro, que además dejó la
--   Primeira en 2020. Confundirlos partiría los dos historiales.
--
--   'B-SAD' es Belenenses SAD, la escisión que jugó en Primeira de 2018 a
--   2022. Se mapea a 'Belenenses' porque es lo que hace football-data.co.uk:
--   su histórico usa ese único nombre de 2014 a 2022, sin separar el club
--   original de la SAD. Aquí se HEREDA esa decisión en vez de tomar una
--   distinta, para que las dos fuentes sigan cuadrando.
--
-- Requiere que la ingesta de football-data haya creado ya los equipos.
-- ============================================================================

DO $$
DECLARE n INTEGER;
BEGIN
  SELECT count(*) INTO n FROM teams
   WHERE league_id IN ('de.bundesliga', 'fr.ligue_1', 'pt.primeira');
  IF n = 0 THEN
    RAISE WARNING 'No hay equipos en las tres ligas europeas nuevas. Corre la '
                  'ingesta histórica antes que este fichero.';
  END IF;
END $$;

INSERT INTO team_aliases (alias, source, team_id)
SELECT v.alias, 'fbref', t.team_id
FROM (VALUES
  -- Bundesliga
  ('de.bundesliga', 'Arminia',         'Bielefeld'),
  ('de.bundesliga', 'Darmstadt 98',    'Darmstadt'),
  ('de.bundesliga', 'Düsseldorf',      'Fortuna Dusseldorf'),
  ('de.bundesliga', 'Gladbach',        'M''gladbach'),
  ('de.bundesliga', 'Hamburger SV',    'Hamburg'),
  ('de.bundesliga', 'Hannover 96',     'Hannover'),
  ('de.bundesliga', 'Hertha BSC',      'Hertha'),
  ('de.bundesliga', 'Mainz 05',        'Mainz'),
  ('de.bundesliga', 'Paderborn 07',    'Paderborn'),
  -- Ligue 1
  ('fr.ligue_1',    'Clermont Foot',   'Clermont'),
  ('fr.ligue_1',    'Paris S-G',       'Paris SG'),
  ('fr.ligue_1',    'Saint-Étienne',   'St Etienne'),
  -- Primeira Liga
  ('pt.primeira',   'AVS Futebol',     'AVS'),
  ('pt.primeira',   'B-SAD',           'Belenenses'),
  ('pt.primeira',   'Braga',           'Sp Braga'),
  ('pt.primeira',   'Paços',           'Pacos Ferreira'),
  ('pt.primeira',   'Sporting CP',     'Sp Lisbon'),
  ('pt.primeira',   'Vitória',         'Guimaraes'),
  ('pt.primeira',   'Vitória Setúbal', 'Setubal')
) AS v(league_id, alias, canonical)
JOIN teams t ON t.league_id = v.league_id AND t.canonical_name = v.canonical
ON CONFLICT (alias, source) DO UPDATE SET team_id = EXCLUDED.team_id;
