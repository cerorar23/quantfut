-- ============================================================================
-- 037 - Historial del chequeo diario de salud
--
-- Del 28-sep al 1-oct-2026 el chequeo de cobertura de bajas falló cada
-- mañana y nadie lo vio: la alerta iba a Telegram sin configurar y la salida
-- del cron quedaba en /var/log dentro del contenedor, que se borra en cada
-- despliegue. Cada pasada del cron (no las del panel) queda aquí.
-- ============================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS health_runs (
    run_id   BIGSERIAL PRIMARY KEY,
    run_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    ok       BOOLEAN NOT NULL,
    results  JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_health_runs_at ON health_runs(run_at DESC);

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qf_readonly') THEN
    GRANT SELECT ON health_runs TO qf_readonly;
  END IF;
END $$;

COMMIT;
