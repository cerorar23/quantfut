-- ============================================================================
-- 033 - Diez ligas "solo sharp" para acelerar la muestra de la puerta
--
-- Pedido del usuario (2026-09-28, "ejecuta todas las palancas"). Solo criterio
-- sharp: `model_enabled = FALSE`, nunca se predicen ni entrenan (y desde hoy
-- tampoco sus equipos cuando juegan una copa: daily.py / train.py).
--
-- Cobertura comprobada el 2026-09-28 (una llamada h2h por liga a The Odds API,
-- eventos con Pinnacle / eventos): Chile 9/10, Turquía 9/9, Suiza 6/6,
-- Dinamarca 6/6, Noruega 8/8, Suecia 8/8, Championship 12/12, Ligue 2 9/9,
-- 2. Bundesliga 9/9, Brasil Série B 8/12. Ids y temporada de API-Football
-- comprobados con /leagues. Descartadas: Bélgica, Australia y Superettan (sin
-- Pinnacle); Colombia, Perú y Ecuador no están en The Odds API.
--
-- Equipos preparados de antemano, como en 024: dejar que el calendario los
-- cree uno a uno descartaba el segundo que se pareciera al primero
-- ('U. Catolica' ~ 'Universidad de Chile') y sin alias de The Odds API no se
-- captura su cierre.
--   * 43 reutilizados: el club ya existe en la Primera de su país. 25
--     comprobados además por el id de API-Football; a mano: Nürnberg,
--     Greuther Fürth (mismo club) y América Mineiro (= 'America MG', id 125).
--   * 127 nuevos, con el nombre de API-Football. Decididos a mano como
--     clubes DISTINTOS pese al parecido: Bolton (~Luton), Annecy (~Nancy),
--     Athletic Club de Minas (~Athletico-PR), Botafogo-SP (~Botafogo RJ).
--   * Nombres de The Odds API revisados; el difuso fallaba en 'Grasshopper
--     Zürich' (daba FC Zürich), 'Queens Park Rangers', 'Clube de Regatas
--     Brasil' y 'AIK'.
-- ON CONFLICT DO NOTHING en alias, como en 024. Comprobado antes: un único
-- choque, 'Athletic Club' (API-Football) ya es el Athletic de Bilbao. Se deja
-- así: el club brasileño se resuelve por su nombre canónico dentro de su liga
-- (el alias del Bilbao no vale fuera de España desde normalize 2026-09-28).
-- ============================================================================
BEGIN;

INSERT INTO leagues (league_id, country, name, tier, fd_code, fd_extra, odds_api_key,
                     cross_league, active, api_football_id, season_style, model_enabled)
VALUES
  ('cl.primera', 'Chile', 'Primera División (Chile)', 1, NULL, FALSE, 'soccer_chile_campeonato',
   FALSE, TRUE, 265, 'calendar', FALSE),
  ('tr.super_lig', 'Turkey', 'Süper Lig', 1, NULL, FALSE, 'soccer_turkey_super_league',
   FALSE, TRUE, 203, 'european', FALSE),
  ('ch.super_league', 'Switzerland', 'Super League (Suiza)', 1, NULL, FALSE, 'soccer_switzerland_superleague',
   FALSE, TRUE, 207, 'european', FALSE),
  ('dk.superliga', 'Denmark', 'Superliga (Dinamarca)', 1, NULL, FALSE, 'soccer_denmark_superliga',
   FALSE, TRUE, 119, 'european', FALSE),
  ('no.eliteserien', 'Norway', 'Eliteserien', 1, NULL, FALSE, 'soccer_norway_eliteserien',
   FALSE, TRUE, 103, 'calendar', FALSE),
  ('se.allsvenskan', 'Sweden', 'Allsvenskan', 1, NULL, FALSE, 'soccer_sweden_allsvenskan',
   FALSE, TRUE, 113, 'calendar', FALSE),
  ('gb.championship', 'England', 'Championship', 2, NULL, FALSE, 'soccer_efl_champ',
   FALSE, TRUE, 40, 'european', FALSE),
  ('fr.ligue_2', 'France', 'Ligue 2', 2, NULL, FALSE, 'soccer_france_ligue_two',
   FALSE, TRUE, 62, 'european', FALSE),
  ('de.bundesliga2', 'Germany', '2. Bundesliga', 2, NULL, FALSE, 'soccer_germany_bundesliga2',
   FALSE, TRUE, 79, 'european', FALSE),
  ('br.serie_b', 'Brazil', 'Série B', 2, NULL, FALSE, 'soccer_brazil_serie_b',
   FALSE, TRUE, 72, 'calendar', FALSE)
ON CONFLICT (league_id) DO NOTHING;

CREATE TEMP TABLE _nuevos (league_id text, nombre text, toa text) ON COMMIT DROP;
INSERT INTO _nuevos VALUES
  ('cl.primera', 'A. Italiano', 'Audax Italiano'),
  ('cl.primera', 'Cobresal', 'Cobresal'),
  ('cl.primera', 'Colo Colo', 'Colo Colo'),
  ('cl.primera', 'Concepción', 'Deportes Concepción'),
  ('cl.primera', 'Coquimbo Unido', 'Coquimbo Unido'),
  ('cl.primera', 'D. La Serena', 'La Serena'),
  ('cl.primera', 'Deportes Limache', 'Deportes Limache'),
  ('cl.primera', 'Everton de Vina', 'Everton de Viña del Mar'),
  ('cl.primera', 'Huachipato', 'Huachipato'),
  ('cl.primera', 'Nublense', 'Ñublense'),
  ('cl.primera', 'O''Higgins', 'O''Higgins'),
  ('cl.primera', 'Palestino', 'Palestino'),
  ('cl.primera', 'U. Catolica', 'Universidad Católica (CHI)'),
  ('cl.primera', 'Union La Calera', 'Union La Calera'),
  ('cl.primera', 'Universidad de Chile', 'Universidad de Chile'),
  ('cl.primera', 'Universidad de Concepcion', 'Universidad de Concepción'),
  ('tr.super_lig', 'Alanyaspor', 'Alanyaspor'),
  ('tr.super_lig', 'Amed', 'Amed SK'),
  ('tr.super_lig', 'Başakşehir', 'Basaksehir'),
  ('tr.super_lig', 'Beşiktaş', 'Besiktas JK'),
  ('tr.super_lig', 'Erzurumspor FK', 'Erzurum BB'),
  ('tr.super_lig', 'Eyüpspor', 'Eyüpspor'),
  ('tr.super_lig', 'Fenerbahçe', 'Fenerbahce'),
  ('tr.super_lig', 'Galatasaray', 'Galatasaray'),
  ('tr.super_lig', 'Gaziantep FK', 'Gazişehir Gaziantep'),
  ('tr.super_lig', 'Gençlerbirliği S.K.', 'Genclerbirligi SK'),
  ('tr.super_lig', 'Göztepe', 'Goztepe'),
  ('tr.super_lig', 'Kasımpaşa', 'Kasimpasa SK'),
  ('tr.super_lig', 'Kocaelispor', 'Kocaelispor'),
  ('tr.super_lig', 'Konyaspor', 'Torku Konyaspor'),
  ('tr.super_lig', 'Rizespor', 'Çaykur Rizespor'),
  ('tr.super_lig', 'Samsunspor', 'Samsunspor'),
  ('tr.super_lig', 'Trabzonspor', 'Trabzonspor'),
  ('tr.super_lig', 'Çorum FK', 'Çorum FK'),
  ('ch.super_league', 'BSC Young Boys', 'BSC Young Boys'),
  ('ch.super_league', 'FC Basel 1893', 'FC Basel'),
  ('ch.super_league', 'FC Lugano', 'FC Lugano'),
  ('ch.super_league', 'FC Luzern', 'FC Luzern'),
  ('ch.super_league', 'FC ST. Gallen', 'FC St Gallen'),
  ('ch.super_league', 'FC Sion', 'FC Sion'),
  ('ch.super_league', 'FC Thun', 'FC Thun'),
  ('ch.super_league', 'FC Vaduz', 'FC Vaduz'),
  ('ch.super_league', 'FC Zurich', 'FC Zurich'),
  ('ch.super_league', 'Grasshoppers', 'Grasshopper Zürich'),
  ('ch.super_league', 'Lausanne', 'FC Lausanne-Sport'),
  ('ch.super_league', 'Servette FC', 'Servette'),
  ('dk.superliga', 'AC Horsens', 'AC Horsens'),
  ('dk.superliga', 'Aarhus', 'AGF Aarhus'),
  ('dk.superliga', 'Brondby', 'Brondby IF'),
  ('dk.superliga', 'FC Copenhagen', 'FC Copenhagen'),
  ('dk.superliga', 'FC Midtjylland', 'FC Midtjylland'),
  ('dk.superliga', 'FC Nordsjaelland', 'FC Nordsjaelland'),
  ('dk.superliga', 'Lyngby', 'Lyngby'),
  ('dk.superliga', 'Odense', 'OB Odense BK'),
  ('dk.superliga', 'Randers FC', 'Randers FC'),
  ('dk.superliga', 'Silkeborg', 'Silkeborg IF'),
  ('dk.superliga', 'Sonderjyske', 'SonderjyskE'),
  ('dk.superliga', 'Viborg', 'Viborg FF'),
  ('no.eliteserien', 'Aalesund', 'Aalesund'),
  ('no.eliteserien', 'Bodo/Glimt', 'Bodø/Glimt'),
  ('no.eliteserien', 'Brann', 'SK Brann'),
  ('no.eliteserien', 'Fredrikstad', 'Fredrikstad FK'),
  ('no.eliteserien', 'Ham-Kam', 'HamKam'),
  ('no.eliteserien', 'KFUM Oslo', 'KFUM'),
  ('no.eliteserien', 'Kristiansund BK', 'Kristiansund BK'),
  ('no.eliteserien', 'Lillestrom', 'Lillestrom'),
  ('no.eliteserien', 'Molde', 'Molde'),
  ('no.eliteserien', 'Rosenborg', 'Rosenborg'),
  ('no.eliteserien', 'Sandefjord', 'Sandefjord'),
  ('no.eliteserien', 'Sarpsborg 08 FF', 'Sarpsborg FK'),
  ('no.eliteserien', 'Start', 'IK Start'),
  ('no.eliteserien', 'Tromso', 'Tromso'),
  ('no.eliteserien', 'Valerenga', 'Vålerenga'),
  ('no.eliteserien', 'Viking', 'Viking FK'),
  ('se.allsvenskan', 'AIK Stockholm', 'AIK'),
  ('se.allsvenskan', 'BK Hacken', 'BK Hacken'),
  ('se.allsvenskan', 'Degerfors IF', 'Degerfors IF'),
  ('se.allsvenskan', 'Djurgardens IF', 'Djurgardens IF'),
  ('se.allsvenskan', 'Gais', 'GAIS'),
  ('se.allsvenskan', 'Halmstad', 'Halmstads BK'),
  ('se.allsvenskan', 'Hammarby FF', 'Hammarby IF'),
  ('se.allsvenskan', 'IF Brommapojkarna', 'IF Brommapojkarna'),
  ('se.allsvenskan', 'IF Elfsborg', 'IF Elfsborg'),
  ('se.allsvenskan', 'IFK Goteborg', 'IFK Goteborg'),
  ('se.allsvenskan', 'Kalmar FF', 'Kalmar FF'),
  ('se.allsvenskan', 'Malmo FF', 'Malmo FF'),
  ('se.allsvenskan', 'Mjallby AIF', 'Mjällby AIF'),
  ('se.allsvenskan', 'Orgryte IS', 'Örgryte IS'),
  ('se.allsvenskan', 'Sirius', 'IK Sirius'),
  ('se.allsvenskan', 'Vasteras SK FK', 'Västerås SK'),
  ('gb.championship', 'Birmingham', 'Birmingham City'),
  ('gb.championship', 'Blackburn', 'Blackburn Rovers'),
  ('gb.championship', 'Bolton', 'Bolton Wanderers'),
  ('gb.championship', 'Bristol City', 'Bristol City'),
  ('gb.championship', 'Charlton', 'Charlton Athletic'),
  ('gb.championship', 'Derby', 'Derby County'),
  ('gb.championship', 'Lincoln', 'Lincoln City'),
  ('gb.championship', 'Millwall', 'Millwall'),
  ('gb.championship', 'Portsmouth', 'Portsmouth'),
  ('gb.championship', 'Preston', 'Preston North End'),
  ('gb.championship', 'Wrexham', 'Wrexham AFC'),
  ('fr.ligue_2', 'Annecy', 'Annecy FC'),
  ('fr.ligue_2', 'Boulogne', 'Boulogne'),
  ('fr.ligue_2', 'Dunkerque', 'USL Dunkerque'),
  ('fr.ligue_2', 'Grenoble', 'Grenoble'),
  ('fr.ligue_2', 'Laval', 'Stade Lavallois'),
  ('fr.ligue_2', 'PAU', 'Pau FC'),
  ('fr.ligue_2', 'RED Star FC 93', 'Red Star'),
  ('fr.ligue_2', 'Rodez', 'Rodez AF'),
  ('fr.ligue_2', 'Sochaux', 'Sochaux'),
  ('de.bundesliga2', '1. FC Kaiserslautern', '1. FC Kaiserslautern'),
  ('de.bundesliga2', '1. FC Magdeburg', '1. FC Magdeburg'),
  ('de.bundesliga2', 'Arminia Bielefeld', 'Arminia Bielefeld'),
  ('de.bundesliga2', 'Dynamo Dresden', 'Dynamo Dresden'),
  ('de.bundesliga2', 'Eintracht Braunschweig', 'Eintracht Braunschweig'),
  ('de.bundesliga2', 'Energie Cottbus', 'FC Energie Cottbus'),
  ('de.bundesliga2', 'Karlsruher SC', 'Karlsruher SC'),
  ('de.bundesliga2', 'VfL Osnabrück', 'VfL Osnabrück'),
  ('br.serie_b', 'Athletic Club', 'Athletic Club (MG)'),
  ('br.serie_b', 'Botafogo SP', 'Botafogo-SP'),
  ('br.serie_b', 'CRB', 'Clube de Regatas Brasil'),
  ('br.serie_b', 'Londrina', 'Londrina'),
  ('br.serie_b', 'Nautico Recife', 'Nautico PE'),
  ('br.serie_b', 'Novorizontino', 'Grêmio Novorizontino'),
  ('br.serie_b', 'Operario-PR', 'Operario PR'),
  ('br.serie_b', 'São Bernardo', 'São Bernardo'),
  ('br.serie_b', 'Vila Nova', 'Vila Nova');

INSERT INTO teams (league_id, canonical_name)
SELECT league_id, nombre FROM _nuevos
ON CONFLICT (league_id, canonical_name) DO NOTHING;

-- (liga actual del club, nombre canónico, API-Football, The Odds API)
CREATE TEMP TABLE _reutilizados (league_id text, canonical text, af text, toa text) ON COMMIT DROP;
INSERT INTO _reutilizados VALUES
  ('gb.premier_league', 'Burnley', 'Burnley', 'Burnley'),
  ('gb.premier_league', 'Cardiff', 'Cardiff', 'Cardiff City'),
  ('gb.premier_league', 'Middlesbrough', 'Middlesbrough', 'Middlesbrough'),
  ('gb.premier_league', 'Norwich', 'Norwich', 'Norwich City'),
  ('gb.premier_league', 'QPR', 'QPR', 'Queens Park Rangers'),
  ('gb.premier_league', 'Sheffield United', 'Sheffield Utd', 'Sheffield United'),
  ('gb.premier_league', 'Southampton', 'Southampton', 'Southampton'),
  ('gb.premier_league', 'Stoke', 'Stoke City', 'Stoke City'),
  ('gb.premier_league', 'Swansea', 'Swansea', 'Swansea City'),
  ('gb.premier_league', 'Watford', 'Watford', 'Watford'),
  ('gb.premier_league', 'West Brom', 'West Brom', 'West Bromwich Albion'),
  ('gb.premier_league', 'West Ham', 'West Ham', 'West Ham United'),
  ('gb.premier_league', 'Wolves', 'Wolves', 'Wolverhampton Wanderers'),
  ('fr.ligue_1', 'Clermont', 'Clermont Foot', 'Clermont'),
  ('fr.ligue_1', 'Dijon', 'Dijon', 'Dijon'),
  ('fr.ligue_1', 'Guingamp', 'Guingamp', 'Guingamp'),
  ('fr.ligue_1', 'Metz', 'Metz', 'Metz'),
  ('fr.ligue_1', 'Montpellier', 'Montpellier', 'Montpellier'),
  ('fr.ligue_1', 'Nancy', 'Nancy', 'Nancy'),
  ('fr.ligue_1', 'Nantes', 'Nantes', 'Nantes'),
  ('fr.ligue_1', 'Reims', 'Reims', 'Stade de Reims'),
  ('fr.ligue_1', 'St Etienne', 'Saint Etienne', 'Saint Etienne'),
  ('de.bundesliga', 'Heidenheim', '1. FC Heidenheim', '1. FC Heidenheim'),
  ('de.bundesliga', 'Nurnberg', '1. FC Nürnberg', '1. FC Nürnberg'),
  ('de.bundesliga', 'St Pauli', 'FC St. Pauli', 'FC St. Pauli'),
  ('de.bundesliga', 'Hannover', 'Hannover 96', 'Hannover 96'),
  ('de.bundesliga', 'Hertha', 'Hertha BSC', 'Hertha Berlin'),
  ('de.bundesliga', 'Holstein Kiel', 'Holstein Kiel', 'Holstein Kiel'),
  ('de.bundesliga', 'Darmstadt', 'SV Darmstadt 98', 'SV Darmstadt 98'),
  ('de.bundesliga', 'Greuther Furth', 'SpVgg Greuther Fürth', 'Greuther Fürth'),
  ('de.bundesliga', 'Bochum', 'VfL Bochum', 'VfL Bochum'),
  ('de.bundesliga', 'Wolfsburg', 'VfL Wolfsburg', 'VfL Wolfsburg'),
  ('br.serie_a', 'America MG', 'America Mineiro', 'América Mineiro'),
  ('br.serie_a', 'Atletico GO', 'Atletico Goianiense', 'Atletico Goianiense'),
  ('br.serie_a', 'Avai', 'Avai', 'Avai'),
  ('br.serie_a', 'Ceara', 'Ceara', 'Ceará'),
  ('br.serie_a', 'Criciuma', 'Criciuma', 'Criciuma'),
  ('br.serie_a', 'Cuiaba', 'Cuiaba', 'Cuiabá'),
  ('br.serie_a', 'Fortaleza', 'Fortaleza EC', 'Fortaleza'),
  ('br.serie_a', 'Goias', 'Goias', 'Goiás'),
  ('br.serie_a', 'Juventude', 'Juventude', 'Juventude'),
  ('br.serie_a', 'Ponte Preta', 'Ponte Preta', 'Ponte Preta'),
  ('br.serie_a', 'Sport Recife', 'Sport Recife', 'Sport Recife');

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
