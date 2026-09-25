-- Usuario de solo lectura para Grafana.
-- Grafana NUNCA debe conectarse con el usuario de la aplicación: un panel mal
-- escrito no puede romper datos que no puede escribir.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qf_readonly') THEN
    EXECUTE format('CREATE ROLE qf_readonly LOGIN PASSWORD %L',
                   coalesce(current_setting('quantfut.grafana_password', true),
                            'cambia_esta_password'));
  END IF;
END $$;

GRANT CONNECT ON DATABASE quantfut TO qf_readonly;
GRANT USAGE ON SCHEMA public TO qf_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO qf_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO qf_readonly;

-- Vistas auxiliares para los paneles
CREATE OR REPLACE VIEW v_clv_daily AS
SELECT date_trunc('day', r.settled_at)::date AS dia,
       count(*)                              AS picks,
       avg(r.clv_pct)                        AS clv_medio,
       avg(CASE WHEN r.beat_close THEN 1.0 ELSE 0.0 END) * 100 AS pct_batio_cierre,
       sum(r.profit_units)                   AS pnl_unidades,
       sum(p.stake_units)                    AS expuesto
FROM pick_results r JOIN picks p USING (pick_id)
GROUP BY 1 ORDER BY 1;

CREATE OR REPLACE VIEW v_odds_growth AS
SELECT date_trunc('day', captured_at)::date AS dia,
       count(*)                             AS snapshots,
       count(DISTINCT match_id)             AS partidos,
       count(DISTINCT bookmaker)            AS casas
FROM odds_snapshots
GROUP BY 1 ORDER BY 1;

CREATE OR REPLACE VIEW v_calibration_bins AS
SELECT c.model_version, c.window_end, c.n_obs, c.rps, c.rps_market,
       b ->> 'bin'                        AS bucket,
       (b ->> 'predicted')::float         AS predicho,
       (b ->> 'observed')::float          AS observado,
       (b ->> 'n')::int                   AS n,
       (b ->> 'within_2se')::boolean      AS dentro_de_2se
FROM calibration_runs c, jsonb_array_elements(c.bins) b
WHERE (b ->> 'n')::int > 0;

GRANT SELECT ON v_clv_daily, v_odds_growth, v_calibration_bins TO qf_readonly;
