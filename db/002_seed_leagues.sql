-- 7 ligas: 3 de referencia (benchmark y credibilidad),
-- 3 de LatAm (menos competencia, público hispanohablante),
-- 1 "huérfana" (buenos datos, pocos modelos encima).
INSERT INTO leagues (league_id, country, name, tier, fd_code, fd_extra, odds_api_key) VALUES
  ('gb.premier_league', 'England',   'Premier League',           1, 'E0',  FALSE, 'soccer_epl'),
  ('es.laliga',         'Spain',     'LaLiga',                   1, 'SP1', FALSE, 'soccer_spain_la_liga'),
  ('it.serie_a',        'Italy',     'Serie A',                  1, 'I1',  FALSE, 'soccer_italy_serie_a'),
  ('mx.liga_mx',        'Mexico',    'Liga MX',                  1, 'MEX', TRUE,  'soccer_mexico_ligamx'),
  ('br.serie_a',        'Brazil',    'Brasileirão Série A',      1, 'BRA', TRUE,  'soccer_brazil_campeonato'),
  ('ar.primera',        'Argentina', 'Liga Profesional',         1, 'ARG', TRUE,  'soccer_argentina_primera_division'),
  ('nl.eredivisie',     'Netherlands','Eredivisie',              1, 'N1',  FALSE, 'soccer_netherlands_eredivisie')
ON CONFLICT (league_id) DO NOTHING;
