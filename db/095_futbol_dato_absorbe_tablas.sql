-- 095: pasa a `futbol.dato` lo que ya estaba en las tablas por tipo del esquema `futbol` (migraciones 085-090 de la
-- rama de trabajo, aplicadas en producción el 1-nov-2026) y retira esas tablas para que quede UNA sola.
--
-- Solo hace algo si esas tablas existen (en una base nueva no existen y esta migración no toca nada). Todo en una
-- transacción: si el número de filas de algún tipo no cuadra con el de la tabla de origen, se deshace entera.
-- Antes de aplicarla en producción: `pg_dump -n futbol` (respaldo en ~/backups). Las tablas absorbidas eran
-- derivadas y reconstruibles desde los originales (archivo de SofaScore y tablas de FotMob).
BEGIN;

DO $migracion$
DECLARE falta TEXT;
BEGIN
    IF to_regclass('futbol.jugador_partido') IS NULL THEN
        RAISE NOTICE '095: no hay tablas por tipo que absorber';
        RETURN;
    END IF;

    -- jugador
    INSERT INTO futbol.dato (match_id, tipo, side, jugador_id, fuente, recibido_en, pit, nombre, id_en_fuente, posicion,
        posicion_id, camiseta, titular, edad, valor_mercado, minutos, nota, goles, asistencias, xa, tiros_puerta,
        tiros_fuera, tiros_bloq, grandes_ocasiones_creadas, grandes_ocasiones_falladas, pases, pases_acertados,
        balones_largos, balones_largos_acertados, centros, centros_acertados, duelos_ganados, duelos_perdidos,
        aereos_ganados, aereos_perdidos, entradas, entradas_ganadas, intercepciones, despejes, recuperaciones,
        perdidas, faltas, faltas_recibidas, fuera_juego, toques, paradas, km, sprints, vel_max)
    SELECT j.match_id, 'jugador', j.side, j.jugador_id, j.fuente, COALESCE(e.recibido_en, now()), j.pit, j.nombre,
           j.id_en_fuente, j.posicion, j.posicion_id, j.camiseta, j.titular, j.edad, j.valor_mercado, j.minutos, j.nota,
           j.goles, j.asistencias, j.xa, j.tiros_puerta, j.tiros_fuera, j.tiros_bloq, j.grandes_ocasiones_creadas,
           j.grandes_ocasiones_falladas, j.pases, j.pases_acertados, j.balones_largos, j.balones_largos_acertados,
           j.centros, j.centros_acertados, j.duelos_ganados, j.duelos_perdidos, j.aereos_ganados, j.aereos_perdidos,
           j.entradas, j.entradas_ganadas, j.intercepciones, j.despejes, j.recuperaciones, j.perdidas, j.faltas,
           j.faltas_recibidas, j.fuera_juego, j.toques, j.paradas, j.km, j.sprints, j.vel_max
      FROM futbol.jugador_partido j
      LEFT JOIN futbol.entidad_fuente e ON e.match_id = j.match_id AND e.entidad = 'jugador_partido'
    ON CONFLICT DO NOTHING;

    -- baja
    INSERT INTO futbol.dato (match_id, tipo, side, jugador_id, fuente, recibido_en, pit, nombre, id_en_fuente, estado,
                             motivo_codigo, descripcion, regreso_texto, regreso_fecha)
    SELECT b.match_id, 'baja', b.side, b.jugador_id, b.fuente, COALESCE(e.recibido_en, now()), b.pit, b.nombre,
           b.id_en_fuente, b.tipo, b.motivo_codigo, b.descripcion, b.regreso_texto, b.regreso_fecha
      FROM futbol.baja b
      LEFT JOIN futbol.entidad_fuente e ON e.match_id = b.match_id AND e.entidad = 'baja'
    ON CONFLICT DO NOTHING;

    -- alineacion
    INSERT INTO futbol.dato (match_id, tipo, side, fuente, recibido_en, pit, formacion, confirmada, completa)
    SELECT a.match_id, 'alineacion', a.side, a.fuente, COALESCE(e.recibido_en, now()), a.pit, a.formacion,
           a.confirmada, a.completa
      FROM futbol.alineacion a
      LEFT JOIN futbol.entidad_fuente e ON e.match_id = a.match_id AND e.entidad = 'alineacion'
    ON CONFLICT DO NOTHING;

    -- entrenador
    INSERT INTO futbol.dato (match_id, tipo, side, fuente, recibido_en, id_en_fuente, nombre)
    SELECT t.match_id, 'entrenador', t.side, t.fuente, COALESCE(e.recibido_en, now()), t.entrenador_id, t.nombre
      FROM futbol.entrenador t
      LEFT JOIN futbol.entidad_fuente e ON e.match_id = t.match_id AND e.entidad = 'entrenador'
    ON CONFLICT DO NOTHING;

    -- contexto (el estadio ya no se repite aquí: vive en el tipo `estadio`)
    INSERT INTO futbol.dato (match_id, tipo, fuente, recibido_en, arbitro_partidos, arbitro_amarillas, arbitro_rojas,
                             arbitro_doble_amarilla, arbitro_pais, ronda, descuento_1t, descuento_2t,
                             goles_local_1t, goles_visita_1t)
    SELECT c.match_id, 'contexto', c.fuente, COALESCE(e.recibido_en, now()), c.arbitro_partidos, c.arbitro_amarillas,
           c.arbitro_rojas, c.arbitro_doble_amarilla, c.arbitro_pais, c.ronda, c.descuento_1t, c.descuento_2t,
           c.goles_local_1t, c.goles_visita_1t
      FROM futbol.contexto c
      LEFT JOIN futbol.entidad_fuente e ON e.match_id = c.match_id AND e.entidad = 'contexto'
    ON CONFLICT DO NOTHING;

    -- tiro
    INSERT INTO futbol.dato (match_id, tipo, side, jugador_id, evento, fuente, recibido_en, nombre, minuto, segundo,
                             resultado, situacion, parte_cuerpo, x, y, boca, boca_x, boca_y, boca_z, xg, xgot)
    SELECT t.match_id, 'tiro', t.side, COALESCE(t.jugador_id, 0), t.tiro_id, t.fuente, COALESCE(e.recibido_en, now()),
           t.jugador, t.minuto, t.segundo, t.resultado, t.situacion, t.parte_cuerpo, t.x, t.y, t.boca, t.boca_x,
           t.boca_y, t.boca_z, t.xg, t.xgot
      FROM futbol.tiro t
      LEFT JOIN futbol.entidad_fuente e ON e.match_id = t.match_id AND e.entidad = 'tiro'
    ON CONFLICT DO NOTHING;

    -- incidencia
    INSERT INTO futbol.dato (match_id, tipo, side, jugador_id, evento, fuente, recibido_en, subtipo, clase, minuto,
                             anadido, nombre, jugador2_id, jugador2, razon, marcador_local, marcador_visita)
    SELECT i.match_id, 'incidencia', COALESCE(i.side, ''), COALESCE(i.jugador_id, 0), i.orden, i.fuente,
           COALESCE(e.recibido_en, now()), i.tipo, i.clase, i.minuto, i.anadido, i.jugador, i.jugador2_id, i.jugador2,
           i.razon, i.marcador_local, i.marcador_visita
      FROM futbol.incidencia i
      LEFT JOIN futbol.entidad_fuente e ON e.match_id = i.match_id AND e.entidad = 'incidencia'
    ON CONFLICT DO NOTHING;

    -- equipo
    INSERT INTO futbol.dato (match_id, tipo, side, fuente, recibido_en, posesion, xgot, grandes_ocasiones_creadas,
        grandes_ocasiones_falladas, tiros_fuera, tiros_bloq, tiros_dentro_area, tiros_fuera_area, paradas,
        goles_evitados, faltas, tiros_libres, fuera_juego, pases, pases_acertados, balones_largos_acertados,
        centros_acertados, entradas, intercepciones, recuperaciones, despejes, perdidas, toques_area_rival,
        entradas_ultimo_tercio, saques_banda, saques_puerta, km, sprints)
    SELECT s.match_id, 'equipo', s.side, s.fuente, COALESCE(e.recibido_en, now()), s.posesion, s.xgot,
           s.grandes_ocasiones, s.grandes_ocasiones_falladas, s.tiros_fuera, s.tiros_bloqueados, s.tiros_dentro_area,
           s.tiros_fuera_area, s.paradas, s.goles_evitados, s.faltas, s.tiros_libres, s.fuera_juego, s.pases,
           s.pases_acertados, s.balones_largos_acertados, s.centros_acertados, s.entradas, s.intercepciones,
           s.recuperaciones, s.despejes, s.perdidas, s.toques_area_rival, s.entradas_ultimo_tercio, s.saques_banda,
           s.saques_puerta, s.km, s.sprints
      FROM futbol.estadistica_equipo s
      LEFT JOIN futbol.entidad_fuente e ON e.match_id = s.match_id AND e.entidad = 'estadistica_equipo'
    ON CONFLICT DO NOTHING;

    -- cuadre: cada tipo debe tener tantas filas como su tabla de origen
    SELECT string_agg(c.tipo || ' ' || c.origen || '<>' || COALESCE(d.n, 0), ', ') INTO falta
      FROM (SELECT 'jugador' tipo, count(*) origen FROM futbol.jugador_partido
            UNION ALL SELECT 'baja', count(*) FROM futbol.baja
            UNION ALL SELECT 'alineacion', count(*) FROM futbol.alineacion
            UNION ALL SELECT 'entrenador', count(*) FROM futbol.entrenador
            UNION ALL SELECT 'contexto', count(*) FROM futbol.contexto
            UNION ALL SELECT 'tiro', count(*) FROM futbol.tiro
            UNION ALL SELECT 'incidencia', count(*) FROM futbol.incidencia
            UNION ALL SELECT 'equipo', count(*) FROM futbol.estadistica_equipo) c
      LEFT JOIN (SELECT tipo, count(*) n FROM futbol.dato
                  WHERE tipo IN ('jugador','baja','alineacion','entrenador','contexto','tiro','incidencia','equipo')
                    AND fuente IN ('sofascore','fotmob','api_football') GROUP BY tipo) d USING (tipo)
     WHERE c.origen <> COALESCE(d.n, 0);
    IF falta IS NOT NULL THEN
        RAISE EXCEPTION '095: no cuadran las filas absorbidas (%)', falta;
    END IF;

    -- retirada de lo absorbido
    DROP VIEW IF EXISTS futbol.v_alineacion_prevista, futbol.v_arbitro_partido, futbol.v_baja,
                        futbol.v_baja_previa_unica, futbol.v_clima_partido, futbol.v_estadio, futbol.v_jugador_partido;
    DROP FUNCTION IF EXISTS futbol.cargar_api_football();
    DROP FUNCTION IF EXISTS futbol.retirar_redundantes();
    DROP TABLE futbol.entidad_fuente, futbol.jugador_partido, futbol.baja, futbol.alineacion, futbol.entrenador,
               futbol.contexto, futbol.tiro, futbol.incidencia, futbol.estadistica_equipo;
    DELETE FROM futbol.prioridad_entidad WHERE entidad IN ('jugador_partido', 'estadistica_equipo', 'altitud', 'cuota');
END
$migracion$;

-- clima y estadio nunca estuvieron en tablas por tipo: se llenan desde sus tablas de origen
SELECT futbol.cargar_clima();
SELECT futbol.cargar_estadio();

COMMIT;
