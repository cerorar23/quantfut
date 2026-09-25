-- ============================================================================
-- 024 - Equipos de LaLiga 2 y Serie B, revisados uno a uno (requiere 023)
--
-- Ninguno se deja al emparejamiento automático. Ensayo en seco del
-- 2026-09-25 (calendario real de API-Football a 21 días y lista de equipos de
-- The Odds API, que no cuesta créditos):
--
-- 1. REUTILIZADOS (19): ya existen con su historia en LaLiga / Serie A. Sin
--    esto el calendario los habría creado otra vez bajo la liga nueva.
-- 2. NUEVOS (22): no están en el catálogo. Nombre canónico = el de
--    API-Football, que es la fuente del calendario y de los resultados.
-- 3. Casos que el ensayo dejó pendientes, decididos a mano:
--      Sporting Gijon  ~ 'Sp Gijon' (73)       -> MISMO club: se reutiliza
--      AD Ceuta FC     ~ 'Celta' (62)           -> club distinto: nuevo
--      Real Sociedad II ~ 'Real Sociedad' (90)  -> filial, club distinto: nuevo
--      Celta de Vigo II ~ 'Celta Vigo' (77)     -> filial, club distinto: nuevo
--      Ascoli          ~ 'Napoli' (67)          -> club distinto: nuevo
--      Modena          ~ 'Monza' (73)           -> club distinto: nuevo
--    Real Sociedad II llega a 90, el umbral de aceptación automática: el
--    difuso habría fusionado el filial con el primer equipo.
--
-- Alias de The Odds API para TODOS: sin ellos su cierre de Pinnacle no se
-- empareja ('Cádiz CF', 'Celta Fortuna', 'US Catanzaro 1929'...) y la oferta
-- se queda sin vara en silencio.
--
-- ON CONFLICT DO NOTHING en los alias, NO DO UPDATE: si un alias ya apunta a
-- otro equipo, se deja como está y se revisa; reasignarlo en silencio sería
-- justo la contaminación que esta migración existe para evitar.
-- ============================================================================
BEGIN;

-- Equipos nuevos --------------------------------------------------------------
CREATE TEMP TABLE _nuevos (league_id text, nombre text, toa text) ON COMMIT DROP;
INSERT INTO _nuevos VALUES
  ('es.laliga2', 'AD Ceuta FC',      'AD Ceuta FC'),
  ('es.laliga2', 'Albacete',         'Albacete'),
  ('es.laliga2', 'Burgos',           'Burgos CF'),
  ('es.laliga2', 'Castellón',        'CD Castellón'),
  ('es.laliga2', 'Celta de Vigo II', 'Celta Fortuna'),
  ('es.laliga2', 'Eldense',          'CD Eldense'),
  ('es.laliga2', 'FC Andorra',       'Andorra CF'),
  ('es.laliga2', 'Real Sociedad II', 'Real Sociedad B'),
  ('es.laliga2', 'Sabadell',         'Sabadell FC'),
  ('es.laliga2', 'Tenerife',         'Tenerife'),
  ('it.serie_b', 'Arezzo',           'Arezzo'),
  ('it.serie_b', 'Ascoli',           'Ascoli'),
  ('it.serie_b', 'Avellino',         'Avellino'),
  ('it.serie_b', 'Carrarese',        'Carrarese'),
  ('it.serie_b', 'Catanzaro',        'US Catanzaro 1929'),
  ('it.serie_b', 'Juve Stabia',      'Juve Stabia'),
  ('it.serie_b', 'Mantova',          'Mantova'),
  ('it.serie_b', 'Modena',           'Modena'),
  ('it.serie_b', 'Padova',           'Padova'),
  ('it.serie_b', 'Sudtirol',         'Südtirol'),
  ('it.serie_b', 'Vicenza Virtus',   'Vicenza'),
  ('it.serie_b', 'Virtus Entella',   'Virtus Entella');

INSERT INTO teams (league_id, canonical_name)
SELECT league_id, nombre FROM _nuevos
ON CONFLICT (league_id, canonical_name) DO NOTHING;

-- Equipos reutilizados: (liga actual del club, nombre canónico, API-Football, The Odds API)
CREATE TEMP TABLE _reutilizados (league_id text, canonical text, af text, toa text) ON COMMIT DROP;
INSERT INTO _reutilizados VALUES
  ('es.laliga',  'Almeria',    'Almeria',       'Almería'),
  ('es.laliga',  'Cadiz',      'Cadiz',         'Cádiz CF'),
  ('es.laliga',  'Cordoba',    'Cordoba',       'Córdoba'),
  ('es.laliga',  'Eibar',      'Eibar',         'SD Eibar'),
  ('es.laliga',  'Girona',     'Girona',        'Girona FC'),
  ('es.laliga',  'Granada',    'Granada CF',    'Granada CF'),
  ('es.laliga',  'Las Palmas', 'Las Palmas',    'Las Palmas'),
  ('es.laliga',  'Leganes',    'Leganes',       'Leganés'),
  ('es.laliga',  'Mallorca',   'Mallorca',      'Mallorca'),
  ('es.laliga',  'Oviedo',     'Oviedo',        'Oviedo'),
  ('es.laliga',  'Sp Gijon',   'Sporting Gijon','Sporting Gijón'),
  ('es.laliga',  'Valladolid', 'Valladolid',    'Real Valladolid CF'),
  ('it.serie_a', 'Benevento',  'Benevento',     'Benevento'),
  ('it.serie_a', 'Cesena',     'Cesena',        'Cesena FC'),
  ('it.serie_a', 'Cremonese',  'Cremonese',     'Cremonese'),
  ('it.serie_a', 'Empoli',     'Empoli',        'Empoli'),
  ('it.serie_a', 'Verona',     'Hellas Verona', 'Hellas Verona'),
  ('it.serie_a', 'Palermo',    'Palermo',       'Palermo'),
  ('it.serie_a', 'Pisa',       'Pisa',          'Pisa'),
  ('it.serie_a', 'Sampdoria',  'Sampdoria',     'Sampdoria');

-- Si falta alguno de los reutilizados, la migración se aborta entera: un alias
-- colgando de un equipo inexistente dejaría el club fuera sin avisar.
DO $$
DECLARE faltan text;
BEGIN
  SELECT string_agg(r.canonical, ', ') INTO faltan
  FROM _reutilizados r
  LEFT JOIN teams t ON t.league_id = r.league_id AND t.canonical_name = r.canonical
  WHERE t.team_id IS NULL;
  IF faltan IS NOT NULL THEN
    RAISE EXCEPTION 'Equipos a reutilizar que no existen: %', faltan;
  END IF;
END $$;

-- Alias ------------------------------------------------------------------------
INSERT INTO team_aliases (alias, source, team_id)
SELECT n.nombre, 'api_football', t.team_id
FROM _nuevos n JOIN teams t ON t.league_id = n.league_id AND t.canonical_name = n.nombre
UNION ALL
SELECT n.toa, 'odds_api', t.team_id
FROM _nuevos n JOIN teams t ON t.league_id = n.league_id AND t.canonical_name = n.nombre
UNION ALL
SELECT r.af, 'api_football', t.team_id
FROM _reutilizados r JOIN teams t ON t.league_id = r.league_id AND t.canonical_name = r.canonical
UNION ALL
SELECT r.toa, 'odds_api', t.team_id
FROM _reutilizados r JOIN teams t ON t.league_id = r.league_id AND t.canonical_name = r.canonical
ON CONFLICT (alias, source) DO NOTHING;

UPDATE unresolved_names u SET resolved = TRUE
WHERE NOT u.resolved AND EXISTS (
  SELECT 1 FROM team_aliases a WHERE a.alias = u.raw_name AND a.source = u.source);

COMMIT;
