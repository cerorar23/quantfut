-- ============================================================================
-- 013 - Alias y altas de API-Football para la temporada 2026
--
-- Primera ingesta de calendario con el plan de pago (2026-09-22). Los nombres
-- que API-Football usa para la temporada EN CURSO no se habían visto nunca:
-- hasta ahora el catálogo venía de football-data.co.uk y de FBref.
--
-- Dos grupos, y la diferencia importa porque el tratamiento es opuesto.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- GRUPO 1 - El mismo club escrito distinto. ALIAS, nunca equipo nuevo.
--
-- Los cinco se quedan por debajo del umbral de auto-aceptación (90) y todos
-- por un motivo mecánico: API-Football conserva la forma societaria completa
-- ('Hamburger SV', 'SC Paderborn 07', '1. FC Köln', 'Estac Troyes') mientras
-- football-data la recorta. Bajar el umbral para capturarlos NO es la
-- solución: es exactamente lo que pondría 'Remo' encima de 'Grêmio' (80).
-- ----------------------------------------------------------------------------
INSERT INTO team_aliases (alias, source, team_id)
SELECT v.alias, 'api_football', t.team_id
FROM (VALUES
  ('Hull City',       'gb.premier_league', 'Hull'),
  ('Hamburger SV',    'de.bundesliga',     'Hamburg'),
  ('SC Paderborn 07', 'de.bundesliga',     'Paderborn'),
  ('1. FC Köln',      'de.bundesliga',     'FC Koln'),
  ('Estac Troyes',    'fr.ligue_1',        'Troyes')
) AS v(alias, league_id, canonical)
JOIN teams t ON t.league_id = v.league_id AND t.canonical_name = v.canonical
ON CONFLICT (alias, source) DO UPDATE SET team_id = EXCLUDED.team_id;

-- ----------------------------------------------------------------------------
-- GRUPO 2 - Clubes que de verdad NO estaban en el catálogo. Equipo nuevo.
--
-- `resolve_or_register` se negó a crearlos, y tenía razón: los cuatro tienen
-- un candidato difuso por encima del suelo de sugerencia (60), así que la
-- función prefiere fallar y avisar antes que arriesgarse a duplicar un club
-- existente. Pero los candidatos son FALSOS y hay que verificarlos a mano:
--
--   'Remo'                      -> 'Grêmio' (80).  Clube do Remo, de Belém.
--                                  No tiene nada que ver con el de Porto Alegre.
--   'Gimnasia M.'               -> 'Gimnasia L.P.' (82). Es la de MENDOZA.
--   'Estudiantes de Rio Cuarto' -> 'Estudiantes L.P.' (60). Córdoba, no La Plata.
--   'Atlante FC'                -> 'Atlas' (67). Clubes distintos.
--
-- Crearlos es el camino SEGURO: un equipo sin historia no entra en el índice
-- del modelo, así que `lambdas()` lo lleva a la media de su liga y la guarda
-- de muestra efectiva impide que se convierta en pick. El camino peligroso
-- habría sido fusionarlos con el club parecido: eso parte un historial en dos
-- y contamina el otro, sin dar ningún error.
-- ----------------------------------------------------------------------------
INSERT INTO teams (league_id, canonical_name)
VALUES
  ('br.serie_a',  'Remo'),
  ('ar.primera',  'Gimnasia Mendoza'),
  ('ar.primera',  'Estudiantes Rio Cuarto'),
  ('mx.liga_mx',  'Atlante')
ON CONFLICT (league_id, canonical_name) DO NOTHING;

INSERT INTO team_aliases (alias, source, team_id)
SELECT v.alias, 'api_football', t.team_id
FROM (VALUES
  ('Remo',                      'br.serie_a', 'Remo'),
  ('Gimnasia M.',               'ar.primera', 'Gimnasia Mendoza'),
  ('Estudiantes de Rio Cuarto', 'ar.primera', 'Estudiantes Rio Cuarto'),
  ('Atlante FC',                'mx.liga_mx', 'Atlante')
) AS v(alias, league_id, canonical)
JOIN teams t ON t.league_id = v.league_id AND t.canonical_name = v.canonical
ON CONFLICT (alias, source) DO UPDATE SET team_id = EXCLUDED.team_id;

-- The Odds API llama distinto a los mismos clubes nuevos. Sin esto el
-- calendario los tendría y la captura de cuotas no los emparejaría.
INSERT INTO team_aliases (alias, source, team_id)
SELECT v.alias, 'odds_api', t.team_id
FROM (VALUES
  ('Remo',                        'br.serie_a', 'Remo'),
  ('Gimnasia Mendoza',            'ar.primera', 'Gimnasia Mendoza'),
  ('Estudiantes de Río Cuarto',   'ar.primera', 'Estudiantes Rio Cuarto'),
  ('Atlante FC',                  'mx.liga_mx', 'Atlante'),
  ('Hull City',                   'gb.premier_league', 'Hull')
) AS v(alias, league_id, canonical)
JOIN teams t ON t.league_id = v.league_id AND t.canonical_name = v.canonical
ON CONFLICT (alias, source) DO UPDATE SET team_id = EXCLUDED.team_id;

UPDATE unresolved_names SET resolved = TRUE
WHERE source IN ('api_football', 'odds_api')
  AND raw_name IN ('Hull City', 'Hamburger SV', 'SC Paderborn 07', '1. FC Köln',
                   'Estac Troyes', 'Remo', 'Gimnasia M.', 'Gimnasia Mendoza',
                   'Estudiantes de Rio Cuarto', 'Estudiantes de Río Cuarto',
                   'Atlante FC');

-- ----------------------------------------------------------------------------
-- NO SE TOCAN: Club Brugge KV, Galatasaray, Sabah FA, Slavia Praha, Viking.
--
-- Juegan la Champions pero sus ligas (Bélgica, Turquía, Azerbaiyán, Chequia,
-- Noruega) no están en el catálogo. Darlos de alta bajo 'eu.ucl' duplicaría
-- clubes y partiría historiales; darlos de alta bajo una liga doméstica que
-- no existe es inventar. Sus partidos se descartan a propósito y quedan en
-- `unresolved_names` como registro de qué se está perdiendo.
-- ----------------------------------------------------------------------------
