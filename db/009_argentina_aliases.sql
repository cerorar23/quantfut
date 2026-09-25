-- ============================================================================
-- 009 - Alias de FBref para Argentina
--
-- Desbloquea el xG de ar.primera, la única liga sin nada de xG. La fuente es
-- el release `match_results` en .rds (ver ingest/xg_worldfootball.py,
-- RDS_ASSETS): 3.261 partidos con xG desde 2017.
--
-- Argentina es el peor caso de nomenclatura de las 10 competiciones porque
-- FBref CAMBIA el nombre del mismo club entre temporadas, y además hay clubes
-- distintos con nombres casi idénticos. Los tres pares que de verdad importan:
--
--   'CC Córdoba' (2020-2023) y 'Cen. Córdoba–SdE' (2024-2025) son el MISMO
--   club, Central Córdoba de Santiago del Estero.
--
--   'Instituto Atlético Central Córdoba' NO es ese club: es Instituto, otro
--   equipo, de la ciudad de Córdoba. Comparten dos tercios del nombre. Un
--   emparejador difuso los mezcla y contamina los dos historiales a la vez.
--
--   'Independiente Rivadavia' (Mendoza) NO es 'Independiente' (Avellaneda).
--
-- SOBRE 'San Martín' A SECAS
-- ---------------------------
-- Aparece solo en 2019, cuando San Martín de San Juan y San Martín de Tucumán
-- estaban los dos en Primera. El emparejador difuso lo resuelve a San Martín
-- de Tucumán con 90,9 puntos, justo por encima del umbral de 90. Es la
-- respuesta correcta (a San Juan FBref lo llama 'San Martín SJ' en esas mismas
-- temporadas), pero depender de un margen de 0,9 puntos para no partir el
-- historial de dos clubes no es aceptable: se fija explícitamente.
-- ============================================================================

DO $$
DECLARE n INTEGER;
BEGIN
  SELECT count(*) INTO n FROM teams WHERE league_id = 'ar.primera';
  IF n = 0 THEN
    RAISE WARNING 'No hay equipos en ar.primera. Corre la ingesta histórica '
                  'antes que este fichero o no se insertará ningún alias.';
  END IF;
END $$;

INSERT INTO team_aliases (alias, source, team_id)
SELECT v.alias, 'fbref', t.team_id
FROM (VALUES
  ('Arg Juniors',                        'Argentinos Jrs'),
  ('Argentinos Jun',                     'Argentinos Jrs'),
  ('Arsenal',                            'Arsenal Sarandi'),
  ('Atlé Tucumán',                       'Atl. Tucuman'),
  ('Tucumán',                            'Atl. Tucuman'),
  ('CA Unión',                           'Union de Santa Fe'),
  ('Unión',                              'Union de Santa Fe'),
  ('CC Córdoba',                         'Central Cordoba'),
  ('Cen. Córdoba–SdE',                   'Central Cordoba'),
  ('Chacarita',                          'Chacarita Juniors'),
  ('Club Atlético Belgrano',             'Belgrano'),
  ('Club Olimpo',                        'Olimpo Bahia Blanca'),
  ('Colón',                              'Colon Santa FE'),
  ('Defensa y Just',                     'Defensa y Justicia'),
  ('Deportivo Riestra',                  'Dep. Riestra'),
  ('Estudiantes',                        'Estudiantes L.P.'),
  ('Estudiantes–LP',                     'Estudiantes L.P.'),
  ('Gimnasia ELP',                       'Gimnasia L.P.'),
  ('Independiente Rivadavia',            'Ind. Rivadavia'),
  ('Instituto Atlético Central Córdoba', 'Instituto'),
  ('Newell''s OB',                       'Newells Old Boys'),
  ('Rafaela',                            'Atl. Rafaela'),
  ('Rosario Cent',                       'Rosario Central'),
  ('San Martín SJ',                      'San Martin S.J.'),
  ('San Martín de San Juan',             'San Martin S.J.'),
  ('San Martín',                         'San Martin T.'),
  ('Sarmiento',                          'Sarmiento Junin'),
  ('Talleres',                           'Talleres Cordoba')
) AS v(alias, canonical)
JOIN teams t ON t.league_id = 'ar.primera' AND t.canonical_name = v.canonical
ON CONFLICT (alias, source) DO UPDATE SET team_id = EXCLUDED.team_id;
