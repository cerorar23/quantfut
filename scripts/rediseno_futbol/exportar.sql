-- Exportación de SOLO LECTURA para el rediseño de los motores de fútbol (1-nov-2026).
-- Lee `matches`, `teams`, `futbol.dato` y `odds_snapshots`; no escribe nada. La salida son bloques CSV separados
-- por una línea `@@ nombre` que `exportar.sh` parte en archivos. Ligas del núcleo + Liga MX (aparte).
\set QUIET on
\pset footer off
BEGIN READ ONLY;
\set P '(SELECT match_id FROM matches WHERE league_id IN (''it.serie_a'',''de.bundesliga'',''fr.ligue_1'',''nl.eredivisie'',''pt.primeira'',''br.serie_a'',''gb.premier_league'',''es.laliga'',''mx.liga_mx'') AND home_goals IS NOT NULL AND kickoff_utc >= ''2014-07-01'')'

\echo '@@ partidos'
COPY (
  SELECT m.match_id, m.league_id, m.season, m.kickoff_utc, m.home_team_id, m.away_team_id,
         th.league_id AS home_league, ta.league_id AS away_league,
         th.canonical_name AS home_name, ta.canonical_name AS away_name,
         m.home_goals, m.away_goals, m.home_goals_ht, m.away_goals_ht, m.home_xg, m.away_xg, m.xg_source,
         m.xg_recorded_at, m.result_recorded_at, m.home_shots, m.away_shots, m.home_shots_target, m.away_shots_target,
         m.home_corners, m.away_corners, m.home_yellow, m.away_yellow, m.home_red, m.away_red,
         m.home_xgot, m.away_xgot, coalesce(m.referee_fotmob, m.referee) AS arbitro_matches
    FROM matches m JOIN :P p USING (match_id)
    JOIN teams th ON th.team_id = m.home_team_id JOIN teams ta ON ta.team_id = m.away_team_id
   ORDER BY m.kickoff_utc
) TO STDOUT WITH CSV HEADER;

\echo '@@ tiros'
COPY (
  SELECT d.match_id, d.side, d.evento AS tiro_id, d.minuto, d.anadido, d.segundos_periodo, d.jugador_id,
         d.portero_id, d.xg, d.xgot, d.situacion, d.resultado, d.parte_cuerpo, d.x, d.y
    FROM futbol.dato d JOIN :P p USING (match_id) WHERE d.tipo = 'tiro'
) TO STDOUT WITH CSV HEADER;

\echo '@@ incidencias'
COPY (
  SELECT d.match_id, d.side, d.evento AS orden, d.subtipo, d.clase, d.minuto, d.anadido, d.jugador_id,
         d.jugador2_id, d.marcador_local, d.marcador_visita, d.anulada
    FROM futbol.dato d JOIN :P p USING (match_id)
   WHERE d.tipo = 'incidencia' AND d.subtipo IN ('goal','card','substitution','inGamePenalty','period')
) TO STDOUT WITH CSV HEADER;

-- Jugadores (props): solo quien jugó; el once es público a T-60, así que «titular» se usa como conocido al sellar.
\echo '@@ jugadores'
COPY (
  SELECT d.match_id, d.side, d.jugador_id, d.posicion, d.titular, d.minutos, d.goles, d.xg, d.tiros_puerta,
         d.tiros_fuera, d.tiros_bloq, d.tiros_totales, d.pases, d.pases_acertados, d.faltas, d.faltas_recibidas
    FROM futbol.dato d JOIN :P p USING (match_id)
   WHERE d.tipo = 'jugador' AND coalesce(d.minutos, 0) > 0
) TO STDOUT WITH CSV HEADER;

\echo '@@ equipo'
COPY (
  SELECT d.match_id, d.side, d.evento AS periodo, d.faltas, d.corners, d.amarillas, d.rojas, d.xg, d.xgot,
         d.tiros_totales, d.tiros_puerta, d.posesion, d.centros_acertados, d.toques_area_rival,
         d.entradas_ultimo_tercio, d.grandes_ocasiones_creadas, d.tiros_dentro_area, d.goles_evitados,
         d.entradas, d.intercepciones, d.despejes, d.recuperaciones
    FROM futbol.dato d JOIN :P p USING (match_id) WHERE d.tipo = 'equipo'
) TO STDOUT WITH CSV HEADER;

\echo '@@ contexto'
COPY (
  SELECT d.match_id, max(d.nombre) FILTER (WHERE d.tipo = 'contexto') AS arbitro,
         max(d.id_en_fuente) FILTER (WHERE d.tipo = 'contexto') AS arbitro_id,
         max(d.asistencia) FILTER (WHERE d.tipo = 'contexto') AS asistencia,
         max(d.estadio_capacidad) FILTER (WHERE d.tipo = 'estadio') AS capacidad,
         max(d.nombre) FILTER (WHERE d.tipo = 'entrenador' AND d.side = 'home') AS entrenador_local,
         max(d.nombre) FILTER (WHERE d.tipo = 'entrenador' AND d.side = 'away') AS entrenador_visita
    FROM futbol.dato d JOIN :P p USING (match_id)
   WHERE d.tipo IN ('contexto','estadio','entrenador') GROUP BY d.match_id
) TO STDOUT WITH CSV HEADER;

-- Cierre 1X2 de football-data y la última cuota de PropLine antes del saque (cualquier mercado), con su hora.
\echo '@@ cuotas'
COPY (
  SELECT DISTINCT ON (o.match_id, o.source, o.bookmaker, o.market, o.selection, o.line)
         o.match_id, o.source, o.bookmaker, o.market, o.selection, o.line, o.price, o.captured_at, o.mins_to_kickoff
    FROM odds_snapshots o JOIN :P p USING (match_id)
   WHERE (o.source = 'football_data' AND o.window_tag = 'close')
      OR (o.source = 'propline' AND o.mins_to_kickoff >= 0)
   ORDER BY o.match_id, o.source, o.bookmaker, o.market, o.selection, o.line, o.mins_to_kickoff
) TO STDOUT WITH CSV HEADER;

\echo '@@ derbis'
COPY (SELECT * FROM futbol.derbi) TO STDOUT WITH CSV HEADER;
\echo '@@ regla_sancion'
COPY (SELECT * FROM futbol.regla_sancion) TO STDOUT WITH CSV HEADER;
\echo '@@ fin'
ROLLBACK;
