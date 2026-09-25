-- ============================================================================
-- 010 - Bundesliga, Ligue 1 y Primeira Liga
--
-- No se añaden por sí mismas, aunque también son ligas apostables. Se añaden
-- porque son las que MÁS partidos de copa estaban tirando a la basura.
--
-- `ingest/uefa_cups.py` descarta todo cruce europeo en el que alguno de los
-- dos equipos no esté en el catálogo. Con 7 ligas se aprovechaban 406 de
-- 3.308 partidos. Medido sobre los descartes:
--
--     Alemania  633    Bélgica  264
--     Francia   464    Rusia    252
--     Portugal  380    Turquía  230
--
-- Estas tres solas se llevaban 1.477. Y los cruces son la ÚNICA información
-- que identifica el término `strength` de model/dixon_coles.py, es decir, lo
-- único que permite comparar la fuerza de una liga con la de otra: dentro de
-- los datos domésticos la suma cero por liga borra esa diferencia.
--
-- Las tres están en el formato PRINCIPAL de football-data.co.uk (columnas
-- ricas: tiros, córners, tarjetas, faltas, árbitro y cuotas de cierre de
-- Pinnacle), no en el "extra", así que no necesitan ningún tratamiento
-- especial en la ingesta.
-- ============================================================================

INSERT INTO leagues (league_id, country, name, tier, fd_code, fd_extra,
                     odds_api_key, cross_league) VALUES
  ('de.bundesliga', 'Germany',  'Bundesliga',    1, 'D1', FALSE,
   'soccer_germany_bundesliga',      FALSE),
  ('fr.ligue_1',    'France',   'Ligue 1',       1, 'F1', FALSE,
   'soccer_france_ligue_one',        FALSE),
  ('pt.primeira',   'Portugal', 'Primeira Liga', 1, 'P1', FALSE,
   'soccer_portugal_primeira_liga',  FALSE)
ON CONFLICT (league_id) DO UPDATE
  SET odds_api_key = EXCLUDED.odds_api_key,
      fd_code      = EXCLUDED.fd_code;

-- IDs de API-Football. SIN VERIFICAR contra la API (no hay clave configurada).
-- Un id equivocado no da error: devuelve 0 partidos y el calendario de esa
-- liga se queda vacío en silencio. Ver scripts/verify_league_ids.py.
UPDATE leagues SET api_football_id = 78, fbref_league_id = 'GER-Bundesliga',
                   season_style = 'european'  WHERE league_id = 'de.bundesliga';
UPDATE leagues SET api_football_id = 61, fbref_league_id = 'FRA-Ligue 1',
                   season_style = 'european'  WHERE league_id = 'fr.ligue_1';
UPDATE leagues SET api_football_id = 94, fbref_league_id = 'POR-Primeira Liga',
                   season_style = 'european'  WHERE league_id = 'pt.primeira';
