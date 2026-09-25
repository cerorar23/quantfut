-- ============================================================================
-- Alias de nombres de equipo de FBref (fuente 'fbref')
--
-- Necesarios para cruzar el xG de worldfootballR_data con los partidos
-- cargados desde football-data.co.uk, que escriben los nombres distinto.
--
-- POR QUÉ ESTÁ ESCRITO A MANO Y NO SE GENERA POR SIMILITUD
-- --------------------------------------------------------
-- El emparejamiento difuso NO sirve aquí, y no por falta de ajuste del umbral:
-- no existe umbral que funcione. Con score ~72 el matcher propone
--
--     'Newcastle Utd'  -> 'manchester united'   (72.7)
--     'Leeds United'   -> 'sheffield united'    (71.4)
--     'Ath Paranaense' -> 'parana'              (60.0)
--
-- que son tres equipos DISTINTOS en cada caso. Fusionarlos arruinaría la
-- estimación de fuerza de dos clubes a la vez y sin dar ningún error. Y al
-- mismo tiempo, por encima de ese score hay aciertos legítimos que se
-- perderían ('Leicester City' -> 'leicester', 78.3).
--
-- Cada línea de abajo está revisada una por una. Las que merecen atención:
--   - 'Ath Paranaense' es Athletico Paranaense (Curitiba), NO Paraná Clube.
--   - 'Atlético' en Liga MX es Atlético de San Luis: es el único "Atlético"
--     de la liga en el periodo cubierto.
--   - 'Morelia' es Monarcas Morelia, registrado como 'Monarcas'.
--   - 'Athletic Club' es el de Bilbao; 'Atlético Madrid' es otro club.
-- ============================================================================

INSERT INTO team_aliases (alias, source, team_id)
SELECT v.alias, 'fbref', t.team_id
FROM (VALUES
    -- Inglaterra: FBref añade el sufijo del nombre largo
    ('gb.premier_league', 'Newcastle Utd',       'Newcastle'),
    ('gb.premier_league', 'Leeds United',        'Leeds'),
    ('gb.premier_league', 'Leicester City',      'Leicester'),
    ('gb.premier_league', 'Norwich City',        'Norwich'),
    ('gb.premier_league', 'Stoke City',          'Stoke'),
    ('gb.premier_league', 'Swansea City',        'Swansea'),
    ('gb.premier_league', 'Cardiff City',        'Cardiff'),
    ('gb.premier_league', 'Ipswich Town',        'Ipswich'),
    ('gb.premier_league', 'Luton Town',          'Luton'),

    -- España
    ('es.laliga',         'Athletic Club',       'Ath Bilbao'),
    ('es.laliga',         'Atlético Madrid',     'Ath Madrid'),
    ('es.laliga',         'Celta Vigo',          'Celta'),
    ('es.laliga',         'Rayo Vallecano',      'Vallecano'),
    ('es.laliga',         'Real Sociedad',       'Sociedad'),

    -- Italia
    ('it.serie_a',        'Hellas Verona',       'Verona'),

    -- Países Bajos
    ('nl.eredivisie',     'ADO Den Haag',        'Den Haag'),
    ('nl.eredivisie',     'De Graafschap',       'Graafschap'),
    ('nl.eredivisie',     'Fortuna Sittard',     'For Sittard'),
    ('nl.eredivisie',     'Go Ahead Eag',        'Go Ahead Eagles'),
    ('nl.eredivisie',     'Heracles Almelo',     'Heracles'),
    ('nl.eredivisie',     'NEC Nijmegen',        'Nijmegen'),
    ('nl.eredivisie',     'RKC Waalwijk',        'Waalwijk'),
    ('nl.eredivisie',     'Sparta R''dam',       'Sparta Rotterdam'),

    -- México
    ('mx.liga_mx',        'UANL',                'Tigres UANL'),
    ('mx.liga_mx',        'UNAM',                'UNAM Pumas'),
    ('mx.liga_mx',        'Guadalajara',         'Guadalajara Chivas'),
    ('mx.liga_mx',        'Santos',              'Santos Laguna'),
    ('mx.liga_mx',        'Morelia',             'Monarcas'),
    ('mx.liga_mx',        'Atlético',            'Atl. San Luis'),

    -- Brasil
    ('br.serie_a',        'Flamengo',            'Flamengo RJ'),
    ('br.serie_a',        'Vasco da Gama',       'Vasco'),
    ('br.serie_a',        'Atlético Mineiro',    'Atletico-MG'),
    ('br.serie_a',        'Ath Paranaense',      'Athletico-PR'),
    ('br.serie_a',        'Atl Goianiense',      'Atletico GO'),
    ('br.serie_a',        'Red Bull Bragantino', 'Bragantino')
) AS v(league_id, alias, canonical)
JOIN teams t ON t.league_id = v.league_id AND t.canonical_name = v.canonical
ON CONFLICT (alias, source) DO NOTHING;

-- Aviso si alguna línea no encontró su equipo. Un alias que no se registra es
-- un fallo mudo: el xG de ese club simplemente no se carga y nadie se entera.
DO $$
DECLARE faltan INT;
BEGIN
    SELECT count(*) INTO faltan
    FROM (VALUES
        ('gb.premier_league','Newcastle'), ('gb.premier_league','Leeds'),
        ('gb.premier_league','Leicester'), ('gb.premier_league','Norwich'),
        ('gb.premier_league','Stoke'),     ('gb.premier_league','Swansea'),
        ('gb.premier_league','Cardiff'),   ('gb.premier_league','Ipswich'),
        ('gb.premier_league','Luton'),
        ('es.laliga','Ath Bilbao'),  ('es.laliga','Ath Madrid'),
        ('es.laliga','Celta'),       ('es.laliga','Vallecano'),
        ('es.laliga','Sociedad'),    ('it.serie_a','Verona'),
        ('nl.eredivisie','Den Haag'),('nl.eredivisie','Graafschap'),
        ('nl.eredivisie','For Sittard'), ('nl.eredivisie','Go Ahead Eagles'),
        ('nl.eredivisie','Heracles'),('nl.eredivisie','Nijmegen'),
        ('nl.eredivisie','Waalwijk'),('nl.eredivisie','Sparta Rotterdam'),
        ('mx.liga_mx','Tigres UANL'),('mx.liga_mx','UNAM Pumas'),
        ('mx.liga_mx','Guadalajara Chivas'), ('mx.liga_mx','Santos Laguna'),
        ('mx.liga_mx','Monarcas'),   ('mx.liga_mx','Atl. San Luis'),
        ('br.serie_a','Flamengo RJ'),('br.serie_a','Vasco'),
        ('br.serie_a','Atletico-MG'),('br.serie_a','Athletico-PR'),
        ('br.serie_a','Atletico GO'),('br.serie_a','Bragantino')
    ) AS v(league_id, canonical)
    WHERE NOT EXISTS (SELECT 1 FROM teams t
                      WHERE t.league_id = v.league_id
                        AND t.canonical_name = v.canonical);
    IF faltan > 0 THEN
        RAISE WARNING 'ALIAS FBREF: % equipos canónicos no existen todavía. '
                      'Vuelve a aplicar este archivo DESPUÉS del backfill '
                      'histórico, o esos clubes se quedarán sin xG.', faltan;
    END IF;
END $$;
