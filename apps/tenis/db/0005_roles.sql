-- 0005: roles de grupo (plan técnico tenis, §A.1). Idempotente.
-- Ninguna contraseña vive aquí: los usuarios con login los crea el despliegue y se añaden a estos grupos.
--   tenis_captura: INSERT en evidencia (sin UPDATE/DELETE/TRUNCATE); estado operativo en tenis_op.
--   tenis_motor:   solo EXECUTE de las funciones de lectura PIT y del sellado (0006); sin SELECT en evidencia.
--   tenis_api:     EXECUTE de lectura PIT; SELECT en pronostico (0006).
--   tenis_lectura: solo SELECT en todo el esquema (G-fuga y copias de comprobación).
-- Si el usuario de migración no puede crear roles (caso de la prueba local), los CREATE ROLE se omiten con
-- aviso y los GRANT también; los crea un superusuario y se vuelve a ejecutar este fichero.
DO $$
DECLARE
    r TEXT;
BEGIN
    FOREACH r IN ARRAY ARRAY['tenis_captura', 'tenis_motor', 'tenis_api', 'tenis_lectura'] LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
            BEGIN
                EXECUTE format('CREATE ROLE %I NOLOGIN', r);
            EXCEPTION WHEN insufficient_privilege THEN
                RAISE NOTICE 'sin permiso para crear el rol %: créalo con un superusuario', r;
            END;
        END IF;
    END LOOP;
END $$;

-- Las funciones nacen con EXECUTE para PUBLIC: se retira antes de conceder nada.
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA tenis FROM PUBLIC;

DO $$
BEGIN
    IF (SELECT count(*) FROM pg_roles
        WHERE rolname IN ('tenis_captura', 'tenis_motor', 'tenis_api', 'tenis_lectura')) = 4 THEN
        GRANT USAGE ON SCHEMA tenis, tenis_op TO tenis_captura, tenis_motor, tenis_api, tenis_lectura;

        -- Captura: solo INSERT en evidencia y su estado operativo.
        GRANT INSERT ON tenis.recibo, tenis.jugador, tenis.jugador_asercion, tenis.jugador_alias,
                        tenis.torneo, tenis.sede, tenis.edicion, tenis.partido, tenis.programa,
                        tenis.resultado, tenis.estadistica, tenis.juego_pbp, tenis.ranking,
                        tenis.precio_mercado, tenis.enlace_evento, tenis.sin_resolver
            TO tenis_captura;
        GRANT USAGE ON ALL SEQUENCES IN SCHEMA tenis TO tenis_captura, tenis_motor;
        GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA tenis_op TO tenis_captura;

        -- Motor y API: solo funciones (la única puerta de lectura).
        GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA tenis TO tenis_motor, tenis_api, tenis_lectura;

        -- Lectura: todo el esquema en solo lectura.
        GRANT SELECT ON ALL TABLES IN SCHEMA tenis TO tenis_lectura;
    ELSE
        RAISE NOTICE 'roles tenis_* ausentes: se omiten los GRANT de 0005';
    END IF;
END $$;
