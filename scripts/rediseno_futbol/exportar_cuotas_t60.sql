-- Solo lectura: último precio de PropLine con al menos 60 minutos de antelación (lo que se tendría al sellar a T-60),
-- por partido, casa, mercado, opción y línea. Mismas ligas que exportar.sql. Uso:
--   ssh quantfut 'docker exec -i quantfut-db-1 psql -U qf -d quantfut -X -v ON_ERROR_STOP=1' < este.sql | gzip > cuotas_t60.csv.gz
\set QUIET on
\pset footer off
BEGIN READ ONLY;
COPY (
  SELECT DISTINCT ON (o.match_id, o.bookmaker, o.market, o.selection, o.line)
         o.match_id, o.source, o.bookmaker, o.market, o.selection, o.line, o.price, o.captured_at, o.mins_to_kickoff
    FROM odds_snapshots o JOIN matches m USING (match_id)
   WHERE o.source = 'propline' AND o.mins_to_kickoff >= 60 AND m.home_goals IS NOT NULL
     AND m.league_id IN ('it.serie_a','de.bundesliga','fr.ligue_1','nl.eredivisie','pt.primeira','br.serie_a',
                         'gb.premier_league','es.laliga','mx.liga_mx')
   ORDER BY o.match_id, o.bookmaker, o.market, o.selection, o.line, o.mins_to_kickoff
) TO STDOUT WITH CSV HEADER;
ROLLBACK;
