-- 0003: la evidencia de tenis es solo-anexar. Disparadores por SENTENCIA: fallan aunque no haya filas
-- afectadas (`DELETE ... WHERE false`), también para el dueño, y también con `TRUNCATE ... CASCADE`.
-- `tenis_op` (estado operativo mutable) NO lleva estos disparadores.
CREATE OR REPLACE FUNCTION tenis.rechazar_cambio() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'evidencia inmutable de tenis: % en %', TG_OP, TG_TABLE_NAME;
END $$;

-- Aplica a una tabla de tenis los dos disparadores. Idempotente (reemplaza los existentes).
-- Se usa aquí y en 0006 (tablas de sellado, que se crean después).
CREATE OR REPLACE FUNCTION tenis.marcar_inmutable(p_tabla TEXT) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    EXECUTE format('DROP TRIGGER IF EXISTS %I ON tenis.%I', p_tabla || '_inmutable', p_tabla);
    EXECUTE format('DROP TRIGGER IF EXISTS %I ON tenis.%I', p_tabla || '_sin_truncate', p_tabla);
    EXECUTE format('CREATE TRIGGER %I BEFORE UPDATE OR DELETE ON tenis.%I FOR EACH STATEMENT '
                   'EXECUTE FUNCTION tenis.rechazar_cambio()', p_tabla || '_inmutable', p_tabla);
    EXECUTE format('CREATE TRIGGER %I BEFORE TRUNCATE ON tenis.%I FOR EACH STATEMENT '
                   'EXECUTE FUNCTION tenis.rechazar_cambio()', p_tabla || '_sin_truncate', p_tabla);
END $$;

DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'fuente', 'recibo', 'jugador', 'jugador_asercion', 'jugador_alias', 'torneo', 'sede', 'edicion',
        'partido', 'programa', 'resultado', 'estadistica', 'juego_pbp', 'ranking', 'precio_mercado',
        'enlace_evento', 'sin_resolver'
    ] LOOP
        PERFORM tenis.marcar_inmutable(t);
    END LOOP;
END $$;
