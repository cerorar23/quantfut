-- Cupos de pronósticos gratis por deporte y cliente (16-nov-2026, decisión del titular).
-- Menú `/control/cupos`. Dos números por (deporte, cliente):
--   destacados_gratis_dia   = en cuántos partidos del día el destacado se ve sin VIP (los de mayor probabilidad);
--   mercados_gratis_partido = cuántos mercados de cada partido se ven sin VIP (los de mayor probabilidad).
-- NULL = sin límite (todo gratis). Lo demás publicado queda VIP con candado.
-- Es presentación: no toca nada sellado, ni el reparto gratis de «alta probabilidad» de la app
-- (`acceso_reglas`, `mobile_free_allocations`). Efecto inmediato; cada cambio queda en `admin_audit`.
BEGIN;

CREATE TABLE IF NOT EXISTS acceso_cupos (
    deporte_id              TEXT NOT NULL CHECK (deporte_id ~ '^[a-z][a-z0-9_]{1,23}$'),
    cliente                 TEXT NOT NULL CHECK (cliente IN ('web', 'app')),
    destacados_gratis_dia   SMALLINT CHECK (destacados_gratis_dia BETWEEN 0 AND 999),
    mercados_gratis_partido SMALLINT CHECK (mercados_gratis_partido BETWEEN 0 AND 999),
    updated_by              TEXT NOT NULL DEFAULT '',
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (deporte_id, cliente)
);

-- Valores de hoy: la web de fútbol abre 3 mercados por partido (GRATIS_WEB) y la app ninguno fuera de sus
-- pronósticos gratis; el destacado es siempre gratis; NBA y tenis van enteros abiertos.
INSERT INTO acceso_cupos (deporte_id, cliente, destacados_gratis_dia, mercados_gratis_partido, updated_by) VALUES
    ('futbol', 'web', NULL, 3,    'migracion'),
    ('futbol', 'app', NULL, 0,    'migracion'),
    ('nba',    'web', NULL, NULL, 'migracion'),
    ('nba',    'app', NULL, NULL, 'migracion'),
    ('tenis',  'web', NULL, NULL, 'migracion'),
    ('tenis',  'app', NULL, NULL, 'migracion')
ON CONFLICT (deporte_id, cliente) DO NOTHING;

COMMIT;
