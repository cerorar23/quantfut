-- Valor esperado contra el cierre SIN margen: la cantidad que decide la
-- puerta comercial desde el 2026-09-23.
--
--     ev_close_pct = (advised_price * closing_prob_devig - 1) * 100
--
-- `clv_pct` compara contra la cuota de cierre CON margen y está sesgado al
-- alza por ese margen. Medido sobre 14.294 partidos: apostar a Pinnacle
-- temprano en todo, sin criterio, da clv_pct -0,32 y ev_close -3,90. Con
-- clv_pct la puerta podía autorizar una estrategia perdedora.
-- clv_pct se sigue guardando y publicando; ya no decide.
--
-- closing_prob_devig pasa a calcularse siempre desde UN snapshot de cierre de
-- la casa sharp con el grupo de selecciones completo. Antes podía mezclar
-- precios de casas distintas cuando a la sharp le faltaba una selección.
--
-- Sin relleno: pick_results y shadow_results estaban vacías al aplicarla.
-- v_clv_daily (Grafana) pertenece a postgres y no se toca aquí.

ALTER TABLE pick_results   ADD COLUMN IF NOT EXISTS ev_close_pct REAL;
ALTER TABLE shadow_results ADD COLUMN IF NOT EXISTS ev_close_pct REAL;

-- CREATE OR REPLACE VIEW solo admite columnas nuevas AL FINAL.
CREATE OR REPLACE VIEW v_track_record AS
SELECT
    date_trunc('month', p.published_at)          AS month,
    p.tier,
    p.market,
    count(*)                                     AS n_picks,
    round(avg(r.clv_pct)::numeric, 3)            AS avg_clv_pct,
    round((avg(CASE WHEN r.beat_close THEN 1.0 ELSE 0.0 END) * 100)::numeric, 1) AS pct_beat_close,
    round(sum(r.profit_units)::numeric, 2)       AS profit_units,
    round((sum(r.profit_units) / NULLIF(sum(p.stake_units), 0) * 100)::numeric, 2) AS roi_pct,
    round(avg(r.ev_close_pct)::numeric, 3)       AS avg_ev_close_pct
FROM picks p
JOIN pick_results r USING (pick_id)
GROUP BY 1, 2, 3
ORDER BY 1 DESC;
