-- Escudos de equipos que ya no están en ninguna clasificación actual
-- (descendidos y rivales de temporadas pasadas que salen en «Forma» y
-- «Cara a cara»). Ids buscados en /teams de API-Football, temporadas
-- 2023-2025, y revisados a mano: los no exactos se comprobaron uno a uno y
-- 'Atletico GO' se corrigió (el más parecido era Atlético-MG). Solo rellena
-- huecos: no pisa ids ni nombres ya puestos por standings.
BEGIN;

UPDATE teams t SET af_team_id = v.af_id,
                   display_name = COALESCE(t.display_name, v.nombre)
FROM (VALUES
  (28402, 459, 'Arsenal Sarandi'),  -- ar.primera · Arsenal Sarandi
  (28428, 448, 'Colon Santa Fe'),  -- ar.primera · Colon Santa FE
  (28403, 439, 'Godoy Cruz'),  -- ar.primera · Godoy Cruz
  (28414, 461, 'San Martin S.J.'),  -- ar.primera · San Martin S.J.
  (41446, 125, 'America Mineiro'),  -- br.serie_a · America MG
  (42213, 144, 'Atletico Goianiense'),  -- br.serie_a · Atletico GO
  (42959, 129, 'Ceara'),  -- br.serie_a · Ceara
  (39928, 140, 'Criciuma'),  -- br.serie_a · Criciuma
  (45234, 1193, 'Cuiaba'),  -- br.serie_a · Cuiaba
  (43733, 154, 'Fortaleza EC'),  -- br.serie_a · Fortaleza
  (39931, 151, 'Goias'),  -- br.serie_a · Goias
  (45235, 152, 'Juventude'),  -- br.serie_a · Juventude
  (39933, 123, 'Sport Recife'),  -- br.serie_a · Sport Recife
  (65735, 176, 'VfL Bochum'),  -- de.bundesliga · Bochum
  (62056, 181, 'SV Darmstadt 98'),  -- de.bundesliga · Darmstadt
  (66959, 180, '1. FC Heidenheim'),  -- de.bundesliga · Heidenheim
  (67567, 191, 'Holstein Kiel'),  -- de.bundesliga · Holstein Kiel
  (67576, 186, 'FC St. Pauli'),  -- de.bundesliga · St Pauli
  (61441, 161, 'VfL Wolfsburg'),  -- de.bundesliga · Wolfsburg
  (73983, 99, 'Clermont Foot'),  -- fr.ligue_1 · Clermont
  (68865, 112, 'Metz'),  -- fr.ligue_1 · Metz
  (68866, 82, 'Montpellier'),  -- fr.ligue_1 · Montpellier
  (68868, 83, 'Nantes'),  -- fr.ligue_1 · Nantes
  (68856, 93, 'Reims'),  -- fr.ligue_1 · Reims
  (68863, 1063, 'Saint Etienne'),  -- fr.ligue_1 · St Etienne
  (1, 44, 'Burnley'),  -- gb.premier_league · Burnley
  (761, 46, 'Leicester'),  -- gb.premier_league · Leicester
  (8, 1359, 'Luton'),  -- gb.premier_league · Luton
  (11, 62, 'Sheffield Utd'),  -- gb.premier_league · Sheffield United
  (768, 41, 'Southampton'),  -- gb.premier_league · Southampton
  (6, 48, 'West Ham'),  -- gb.premier_league · West Ham
  (20, 39, 'Wolves'),  -- gb.premier_league · Wolves
  (17414, 514, 'Salernitana'),  -- it.serie_a · Salernitana
  (35161, 14002, 'Mazatlán'),  -- mx.liga_mx · Mazatlan FC
  (26581, 419, 'Almere City FC'),  -- nl.eredivisie · Almere City
  (21211, 206, 'Heracles'),  -- nl.eredivisie · Heracles
  (21213, 203, 'NAC Breda'),  -- nl.eredivisie · NAC Breda
  (21216, 200, 'Vitesse'),  -- nl.eredivisie · Vitesse
  (25964, 416, 'FC Volendam'),  -- nl.eredivisie · Volendam
  (24274, 417, 'Waalwijk'),  -- nl.eredivisie · Waalwijk
  (83542, 21595, 'AVS'),  -- pt.primeira · AVS
  (77435, 222, 'Boavista'),  -- pt.primeira · Boavista
  (78662, 223, 'Chaves'),  -- pt.primeira · Chaves
  (81103, 231, 'Farense'),  -- pt.primeira · Farense
  (79262, 216, 'Portimonense'),  -- pt.primeira · Portimonense
  (78032, 218, 'Tondela'),  -- pt.primeira · Tondela
  (81705, 810, 'Vizela')  -- pt.primeira · Vizela
) AS v(team_id, af_id, nombre)
WHERE t.team_id = v.team_id AND t.af_team_id IS NULL;

COMMIT;
