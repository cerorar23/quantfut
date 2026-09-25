-- v_clv_daily seguía mostrando solo clv_pct, la vara con margen que 015 dejó
-- de usar para decidir. Se añade el valor esperado al cierre SIN margen.
-- CREATE OR REPLACE VIEW solo admite columnas nuevas AL FINAL; conserva los
-- GRANT a qf_readonly de 004.
-- En el Postgres local la vista pertenece a `postgres`: aplicarla con ese rol.

CREATE OR REPLACE VIEW v_clv_daily AS
SELECT
    date_trunc('day', r.settled_at)::date                      AS dia,
    count(*)                                                    AS picks,
    avg(r.clv_pct)                                              AS clv_medio,
    avg(CASE WHEN r.beat_close THEN 1.0 ELSE 0.0 END) * 100     AS pct_batio_cierre,
    sum(r.profit_units)                                         AS pnl_unidades,
    sum(p.stake_units)                                          AS expuesto,
    avg(r.ev_close_pct)                                         AS ev_cierre_medio
FROM pick_results r
JOIN picks p USING (pick_id)
GROUP BY 1
ORDER BY 1;
