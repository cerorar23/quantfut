-- 0007: el margen se calcula por contrato, no por línea. En un hándicap los dos lados tienen líneas opuestas (-4,5 y +4,5)
-- y agrupar por línea nunca los emparejaba (margen absurdo de -47 %). El contrato ya distingue las alternativas (llevan el
-- punto) y deja la línea principal libre de moverse, así que los dos lados de una misma oferta comparten `contrato_id`.
DROP VIEW nba.cuota_margen;
CREATE VIEW nba.cuota_margen AS
    SELECT partido_id, fuente, casa, mercado, periodo, entidad_id, contrato_id,
           max(abs(linea)) AS linea_abs, count(*)::int AS n_lados, sum(1 / cuota) - 1 AS margen
    FROM nba.cuota_cierre
    GROUP BY partido_id, fuente, casa, mercado, periodo, entidad_id, contrato_id;
GRANT SELECT ON nba.cuota_margen TO nba_escritor, nba_lector;
