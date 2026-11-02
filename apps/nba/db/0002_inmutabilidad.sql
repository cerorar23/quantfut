-- 0002: las tablas de evidencia son solo-anexar. Disparadores por SENTENCIA: fallan aunque no haya
-- filas afectadas (`DELETE ... WHERE false`), también para el dueño y con `TRUNCATE ... CASCADE`.
CREATE FUNCTION nba.rechazar_cambio() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'evidencia inmutable de NBA: % en nba.%', TG_OP, TG_TABLE_NAME;
END $$;

CREATE TRIGGER entidad_inmutable    BEFORE UPDATE OR DELETE ON nba.entidad    FOR EACH STATEMENT EXECUTE FUNCTION nba.rechazar_cambio();
CREATE TRIGGER captura_inmutable    BEFORE UPDATE OR DELETE ON nba.captura    FOR EACH STATEMENT EXECUTE FUNCTION nba.rechazar_cambio();
CREATE TRIGGER dato_inmutable       BEFORE UPDATE OR DELETE ON nba.dato       FOR EACH STATEMENT EXECUTE FUNCTION nba.rechazar_cambio();
CREATE TRIGGER cuota_inmutable      BEFORE UPDATE OR DELETE ON nba.cuota      FOR EACH STATEMENT EXECUTE FUNCTION nba.rechazar_cambio();
CREATE TRIGGER evento_inmutable     BEFORE UPDATE OR DELETE ON nba.evento     FOR EACH STATEMENT EXECUTE FUNCTION nba.rechazar_cambio();
CREATE TRIGGER pronostico_inmutable BEFORE UPDATE OR DELETE ON nba.pronostico FOR EACH STATEMENT EXECUTE FUNCTION nba.rechazar_cambio();

CREATE TRIGGER entidad_sin_truncate    BEFORE TRUNCATE ON nba.entidad    FOR EACH STATEMENT EXECUTE FUNCTION nba.rechazar_cambio();
CREATE TRIGGER captura_sin_truncate    BEFORE TRUNCATE ON nba.captura    FOR EACH STATEMENT EXECUTE FUNCTION nba.rechazar_cambio();
CREATE TRIGGER dato_sin_truncate       BEFORE TRUNCATE ON nba.dato       FOR EACH STATEMENT EXECUTE FUNCTION nba.rechazar_cambio();
CREATE TRIGGER cuota_sin_truncate      BEFORE TRUNCATE ON nba.cuota      FOR EACH STATEMENT EXECUTE FUNCTION nba.rechazar_cambio();
CREATE TRIGGER evento_sin_truncate     BEFORE TRUNCATE ON nba.evento     FOR EACH STATEMENT EXECUTE FUNCTION nba.rechazar_cambio();
CREATE TRIGGER pronostico_sin_truncate BEFORE TRUNCATE ON nba.pronostico FOR EACH STATEMENT EXECUTE FUNCTION nba.rechazar_cambio();
