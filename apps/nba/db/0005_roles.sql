-- 0005: roles de grupo. Los usuarios con contraseña (migración, colectores, API) los crea el despliegue
-- y se agregan a estos grupos; ninguna contraseña vive en el repositorio.
--   nba_escritor: INSERT en las tablas de evidencia, sin UPDATE/DELETE/TRUNCATE.
--   nba_lector:   solo SELECT (la API de lectura).
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nba_escritor') THEN CREATE ROLE nba_escritor NOLOGIN; END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nba_lector') THEN CREATE ROLE nba_lector NOLOGIN; END IF;
END $$;

GRANT USAGE ON SCHEMA nba TO nba_escritor, nba_lector;
GRANT SELECT ON ALL TABLES IN SCHEMA nba TO nba_escritor, nba_lector;
GRANT INSERT ON nba.entidad, nba.captura, nba.dato, nba.cuota, nba.evento, nba.pronostico TO nba_escritor;
