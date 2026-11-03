-- Solo lectura: partidos terminados con cuotas de PropLine desde :desde y, de esas cuotas, el último precio de cada
-- casa/mercado/opción/línea con al menos 60 minutos de antelación (T-60) y el último antes del saque (cierre).
-- Lo usa `remedir_semana.py` (la medición semanal de si el porcentaje de la casa se cumple). Uso:
--   ssh quantfut 'docker exec -i quantfut-db-1 psql -U qf -d quantfut -X -v ON_ERROR_STOP=1 -v desde=2026-10-23' < este.sql
\set QUIET on
\pset footer off
BEGIN READ ONLY;
\echo '@@ partidos'
COPY (
  SELECT m.match_id, m.league_id, m.kickoff_utc, m.home_goals, m.away_goals, m.home_goals_ht, m.away_goals_ht,
         m.home_corners, m.away_corners, m.home_yellow, m.away_yellow, m.home_red, m.away_red
    FROM matches m
   WHERE m.home_goals IS NOT NULL AND m.kickoff_utc >= :'desde'::timestamptz
     AND EXISTS (SELECT 1 FROM odds_snapshots o WHERE o.match_id = m.match_id AND o.source = 'propline')
) TO STDOUT WITH CSV HEADER;
\echo '@@ cuotas_t60'
COPY (
  SELECT DISTINCT ON (o.match_id, o.bookmaker, o.market, o.selection, o.line)
         o.match_id, o.bookmaker, o.market, o.selection, o.line, o.price, o.mins_to_kickoff
    FROM odds_snapshots o JOIN matches m USING (match_id)
   WHERE o.source = 'propline' AND o.mins_to_kickoff >= 60 AND m.home_goals IS NOT NULL AND m.kickoff_utc >= :'desde'::timestamptz
   ORDER BY o.match_id, o.bookmaker, o.market, o.selection, o.line, o.mins_to_kickoff
) TO STDOUT WITH CSV HEADER;
\echo '@@ cuotas_cierre'
COPY (
  SELECT DISTINCT ON (o.match_id, o.bookmaker, o.market, o.selection, o.line)
         o.match_id, o.bookmaker, o.market, o.selection, o.line, o.price, o.mins_to_kickoff
    FROM odds_snapshots o JOIN matches m USING (match_id)
   WHERE o.source = 'propline' AND o.mins_to_kickoff >= 0 AND m.home_goals IS NOT NULL AND m.kickoff_utc >= :'desde'::timestamptz
   ORDER BY o.match_id, o.bookmaker, o.market, o.selection, o.line, o.mins_to_kickoff
) TO STDOUT WITH CSV HEADER;
\echo '@@ fin'
ROLLBACK;
