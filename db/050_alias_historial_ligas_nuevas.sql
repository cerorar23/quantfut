-- ============================================================================
-- 050 - Nombres de football-data revisados a mano para cargar el historial
-- de las ligas "solo sharp" (2026-10-11). Sale del ensayo en seco
-- (`python -m qf.ingest.history_fd ensayo ...`): 86 nombres "dudosos" que el
-- cargador NO resuelve solo, porque se parecen a un club existente.
--
-- Tres bloques:
--   A. Un duplicado que YA existía: el calendario de API-Football creó
--      "Arminia Bielefeld" en la 2. Bundesliga sin ver al "Bielefeld" de la
--      Bundesliga (68 partidos desde 2020). Se fusiona en el antiguo, que se
--      queda el escudo y el id de API-Football. Sin esto, al activar la
--      2. Bundesliga su historia quedaba partida en dos.
--   B. El mismo club escrito de otra forma: alias de football_data.
--   C. Clubes DISTINTOS que solo se parecen (Barnsley/Burnley, Sevilla B/
--      Sevilla, Gaziantepspor/Gaziantep FK…): se crean en la liga que se carga.
--      Ninguno juega hoy en el catálogo (su última temporada es <= 2025/26).
-- Todo se busca por (liga, nombre canónico), nunca por id.
-- ============================================================================
BEGIN;

CREATE FUNCTION pg_temp.equipo(lg text, nombre text) RETURNS bigint AS $$
DECLARE tid bigint;
BEGIN
  SELECT team_id INTO STRICT tid FROM teams WHERE league_id = lg AND canonical_name = nombre;
  RETURN tid;
END $$ LANGUAGE plpgsql;

-- A. Bielefeld --------------------------------------------------------------
DO $$
DECLARE viejo bigint := pg_temp.equipo('de.bundesliga', 'Bielefeld');
        nuevo bigint := pg_temp.equipo('de.bundesliga2', 'Arminia Bielefeld');
        af integer; nombre text;
BEGIN
  SELECT af_team_id, display_name INTO af, nombre FROM teams WHERE team_id = nuevo;
  UPDATE matches SET home_team_id = viejo WHERE home_team_id = nuevo;
  UPDATE matches SET away_team_id = viejo WHERE away_team_id = nuevo;
  UPDATE standings SET team_id = viejo WHERE team_id = nuevo;
  UPDATE team_aliases SET team_id = viejo WHERE team_id = nuevo;
  DELETE FROM teams WHERE team_id = nuevo;
  UPDATE teams SET af_team_id = COALESCE(af_team_id, af),
                   display_name = COALESCE(display_name, nombre)
  WHERE team_id = viejo;
END $$;

-- B. Mismo club, otro nombre ------------------------------------------------
INSERT INTO team_aliases (alias, source, team_id)
SELECT v.alias, 'football_data', pg_temp.equipo(v.lg, v.canonico)
FROM (VALUES
    ('es.laliga2',      'Celta B',        'Celta de Vigo II'),
    ('es.laliga2',      'Ceuta',          'AD Ceuta FC'),
    ('es.laliga2',      'Sociedad B',     'Real Sociedad II'),
    ('de.bundesliga2',  'Braunschweig',   'Eintracht Braunschweig'),
    ('de.bundesliga2',  'Cottbus',        'Energie Cottbus'),
    ('de.bundesliga2',  'Dresden',        'Dynamo Dresden'),
    ('de.bundesliga2',  'Kaiserslautern', '1. FC Kaiserslautern'),
    ('de.bundesliga2',  'Karlsruhe',      'Karlsruher SC'),
    ('de.bundesliga2',  'Magdeburg',      '1. FC Magdeburg'),
    ('de.bundesliga2',  'Osnabruck',      'VfL Osnabrück'),
    ('tr.super_lig',    'Amedspor',       'Amed'),
    ('tr.super_lig',    'Buyuksehyr',     'Başakşehir'),
    ('tr.super_lig',    'Corum',          'Çorum FK'),
    ('tr.super_lig',    'Erzurumspor',    'Erzurumspor FK'),
    ('tr.super_lig',    'Gaziantep',      'Gaziantep FK'),
    ('tr.super_lig',    'Genclerbirligi', 'Gençlerbirliği S.K.'),
    ('tr.super_lig',    'Goztep',         'Göztepe'),
    ('tr.super_lig',    'Kasimpasa',      'Kasımpaşa'),
    ('no.eliteserien',  'Sarpsborg 08',   'Sarpsborg 08 FF'),
    ('se.allsvenskan',  'Djurgarden',     'Djurgardens IF'),
    ('se.allsvenskan',  'Goteborg',       'IFK Goteborg'),
    ('se.allsvenskan',  'Kalmar',         'Kalmar FF'),
    ('se.allsvenskan',  'Mjallby',        'Mjallby AIF'),
    ('se.allsvenskan',  'Orgryte',        'Orgryte IS'),
    ('ch.super_league', 'Young Boys',     'BSC Young Boys')
) AS v(lg, alias, canonico)
ON CONFLICT (alias, source) DO UPDATE SET team_id = EXCLUDED.team_id;

-- C. Clubes distintos que solo se parecen ------------------------------------
-- "Leonesa" (2017/18) y "Cultural Leonesa" (2025/26) son el mismo club con
-- dos nombres en football-data: se crea uno y lleva los dos alias.
CREATE TEMP TABLE nuevos (lg text, nombre text, alias text) ON COMMIT DROP;
INSERT INTO nuevos VALUES
    ('gb.championship', 'Barnsley', 'Barnsley'), ('gb.championship', 'Burton', 'Burton'),
    ('gb.championship', 'Oxford', 'Oxford'), ('gb.championship', 'Plymouth', 'Plymouth'),
    ('gb.championship', 'Rotherham', 'Rotherham'),
    ('gb.championship', 'Sheffield Weds', 'Sheffield Weds'),
    ('es.laliga2', 'Alcorcon', 'Alcorcon'), ('es.laliga2', 'Ath Bilbao B', 'Ath Bilbao B'),
    ('es.laliga2', 'Barcelona B', 'Barcelona B'), ('es.laliga2', 'Ibiza', 'Ibiza'),
    ('es.laliga2', 'Cultural Leonesa', 'Cultural Leonesa'),
    ('es.laliga2', 'Cultural Leonesa', 'Leonesa'),
    ('es.laliga2', 'Logrones', 'Logrones'), ('es.laliga2', 'Lorca', 'Lorca'),
    ('es.laliga2', 'Lugo', 'Lugo'), ('es.laliga2', 'Numancia', 'Numancia'),
    ('es.laliga2', 'Sevilla B', 'Sevilla B'), ('es.laliga2', 'Villarreal B', 'Villarreal B'),
    ('de.bundesliga2', 'Duisburg', 'Duisburg'),
    ('de.bundesliga2', 'Frankfurt FSV', 'Frankfurt FSV'),
    ('de.bundesliga2', 'Regensburg', 'Regensburg'),
    ('it.serie_b', 'Alessandria', 'Alessandria'), ('it.serie_b', 'Bari', 'Bari'),
    ('it.serie_b', 'Catania', 'Catania'), ('it.serie_b', 'Cosenza', 'Cosenza'),
    ('it.serie_b', 'Lecco', 'Lecco'), ('it.serie_b', 'Livorno', 'Livorno'),
    ('it.serie_b', 'Novara', 'Novara'), ('it.serie_b', 'Perugia', 'Perugia'),
    ('it.serie_b', 'Ternana', 'Ternana'), ('it.serie_b', 'Varese', 'Varese'),
    ('it.serie_b', 'Virtus Lanciano', 'Virtus Lanciano'),
    ('fr.ligue_2', 'Arles', 'Arles'), ('fr.ligue_2', 'Orleans', 'Orleans'),
    ('fr.ligue_2', 'Tours', 'Tours'), ('fr.ligue_2', 'Valenciennes', 'Valenciennes'),
    ('tr.super_lig', 'Ad. Demirspor', 'Ad. Demirspor'), ('tr.super_lig', 'Adanaspor', 'Adanaspor'),
    ('tr.super_lig', 'Altay', 'Altay'), ('tr.super_lig', 'Antalyaspor', 'Antalyaspor'),
    ('tr.super_lig', 'Bursaspor', 'Bursaspor'), ('tr.super_lig', 'Denizlispor', 'Denizlispor'),
    ('tr.super_lig', 'Erciyesspor', 'Erciyesspor'),
    ('tr.super_lig', 'Eskisehirspor', 'Eskisehirspor'),
    ('tr.super_lig', 'Gaziantepspor', 'Gaziantepspor'),
    ('tr.super_lig', 'Giresunspor', 'Giresunspor'), ('tr.super_lig', 'Hatayspor', 'Hatayspor'),
    ('tr.super_lig', 'Istanbulspor', 'Istanbulspor'),
    ('tr.super_lig', 'Karabukspor', 'Karabukspor'),
    ('tr.super_lig', 'Kayserispor', 'Kayserispor'),
    ('tr.super_lig', 'Osmanlispor', 'Osmanlispor'), ('tr.super_lig', 'Sivasspor', 'Sivasspor'),
    ('tr.super_lig', 'Umraniyespor', 'Umraniyespor'),
    ('tr.super_lig', 'Yeni Malatyaspor', 'Yeni Malatyaspor'),
    ('no.eliteserien', 'Bryne', 'Bryne'), ('no.eliteserien', 'Haugesund', 'Haugesund'),
    ('no.eliteserien', 'Stromsgodset', 'Stromsgodset'),
    ('se.allsvenskan', 'Helsingborg', 'Helsingborg'),
    ('se.allsvenskan', 'Trelleborgs', 'Trelleborgs'),
    ('dk.superliga', 'Aalborg', 'Aalborg'), ('dk.superliga', 'Vestsjaelland', 'Vestsjaelland'),
    ('ch.super_league', 'Lausanne Ouchy', 'Lausanne Ouchy');

INSERT INTO teams (league_id, canonical_name)
SELECT DISTINCT lg, nombre FROM nuevos
ON CONFLICT (league_id, canonical_name) DO NOTHING;

INSERT INTO team_aliases (alias, source, team_id)
SELECT n.alias, 'football_data', pg_temp.equipo(n.lg, n.nombre) FROM nuevos n
ON CONFLICT (alias, source) DO UPDATE SET team_id = EXCLUDED.team_id;

UPDATE unresolved_names SET resolved = TRUE
WHERE source = 'football_data'
  AND raw_name IN (SELECT alias FROM team_aliases WHERE source = 'football_data');

DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM teams WHERE canonical_name = 'Arminia Bielefeld') THEN
    RAISE EXCEPTION 'db/050: Arminia Bielefeld sigue duplicado';
  END IF;
  IF (SELECT count(*) FROM team_aliases WHERE source = 'football_data' AND alias IN
      ('Celta B', 'Kasimpasa', 'Young Boys', 'Leonesa', 'Sheffield Weds', 'Lausanne Ouchy')) <> 6 THEN
    RAISE EXCEPTION 'db/050: faltan alias revisados';
  END IF;
END $$;

COMMIT;
