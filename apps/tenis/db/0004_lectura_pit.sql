-- 0004: única puerta de lectura del motor (punto en el tiempo, plan §A.4).
-- Todas las funciones *_a_las(corte) devuelven, por clave lógica, la aserción vigente con recibido_en <= corte.
-- Desempate: prioridad de la fuente (menor = mejor), luego recibido_en más reciente, luego id mayor.
-- Regla RETRO: un recibo con retro = true no es visible para un corte posterior a 00:00 UTC del lunes de la
-- semana siguiente al lunes de la semana en que termina la edición del partido (lunes_semana + 7 días).
-- Las funciones son SECURITY DEFINER: el rol del motor solo tiene EXECUTE, no SELECT sobre las tablas (0005).

-- Corte a partir del cual un dato retro de la semana `p_lunes` es visible (estrictamente posterior).
CREATE OR REPLACE FUNCTION tenis.retro_visible(p_corte TIMESTAMPTZ, p_retro BOOLEAN, p_lunes DATE)
RETURNS BOOLEAN LANGUAGE sql IMMUTABLE AS $$
    SELECT NOT p_retro OR p_corte > ((p_lunes + 7)::timestamp AT TIME ZONE 'UTC')
$$;

-- Edición vigente por (torneo, temporada). La regla RETRO se aplica también a la propia edición.
CREATE OR REPLACE FUNCTION tenis.edicion_a_las(p_corte TIMESTAMPTZ) RETURNS SETOF tenis.edicion
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = tenis, pg_temp AS $$
    SELECT DISTINCT ON (e.torneo_id, e.temporada) e.*
    FROM tenis.edicion e
    JOIN tenis.fuente f ON f.fuente = e.fuente
    JOIN tenis.recibo r ON r.recibo_id = e.recibo_id
    WHERE e.recibido_en <= p_corte
      AND tenis.retro_visible(p_corte, r.retro, e.lunes_semana)
    ORDER BY e.torneo_id, e.temporada, f.prioridad_calendario, e.recibido_en DESC, e.edicion_id DESC
$$;

-- Lunes de la semana de fin de la edición de un partido, según la edición vigente en `p_corte`.
-- NULL si la edición aún no era visible: un dato retro de ese partido queda oculto (conservador).
CREATE OR REPLACE FUNCTION tenis.lunes_partido_a_las(p_partido BIGINT, p_corte TIMESTAMPTZ) RETURNS DATE
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = tenis, pg_temp AS $$
    SELECT ev.lunes_semana
    FROM tenis.partido p
    JOIN tenis.edicion e1 ON e1.edicion_id = p.edicion_id
    JOIN tenis.edicion_a_las(p_corte) ev ON ev.torneo_id = e1.torneo_id AND ev.temporada = e1.temporada
    WHERE p.partido_id = p_partido
$$;

-- Lo mismo para TODOS los partidos de una vez (una sola pasada: la edición vigente se calcula una vez, no por fila).
-- Las lecturas `*_a_las` usan ESTA función con LEFT JOIN; la versión por partido de arriba queda como referencia
-- escalar (la usan las pruebas para comprobar que ambas coinciden). Medido: la forma por fila crecía más que
-- linealmente (2.000 partidos 1,9 s; 8.000 partidos 13,7 s) y no escalaba a ~0,5 M.
CREATE OR REPLACE FUNCTION tenis.lunes_por_partido_a_las(p_corte TIMESTAMPTZ)
RETURNS TABLE (partido_id BIGINT, lunes_semana DATE)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = tenis, pg_temp AS $$
    SELECT p.partido_id, ev.lunes_semana
    FROM tenis.partido p
    JOIN tenis.edicion e1 ON e1.edicion_id = p.edicion_id
    JOIN tenis.edicion_a_las(p_corte) ev ON ev.torneo_id = e1.torneo_id AND ev.temporada = e1.temporada
$$;

-- Jugador: aserciones vigentes por (jugador, campo). Sin regla RETRO (no hay partido al que atarla).
CREATE OR REPLACE FUNCTION tenis.jugador_asercion_a_las(p_corte TIMESTAMPTZ) RETURNS SETOF tenis.jugador_asercion
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = tenis, pg_temp AS $$
    SELECT DISTINCT ON (a.jugador_id, a.campo) a.*
    FROM tenis.jugador_asercion a
    JOIN tenis.fuente f ON f.fuente = a.fuente
    WHERE a.recibido_en <= p_corte
    ORDER BY a.jugador_id, a.campo, f.prioridad_calendario, a.recibido_en DESC, a.asercion_id DESC
$$;

-- Alias vigente por (fuente, id de la fuente). Una fila anulada (anula_a apunta a ella, visible en el corte)
-- deja de contar; la fila que la anula puede ser el alias correcto.
CREATE OR REPLACE FUNCTION tenis.jugador_alias_a_las(p_corte TIMESTAMPTZ) RETURNS SETOF tenis.jugador_alias
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = tenis, pg_temp AS $$
    SELECT DISTINCT ON (a.fuente, a.id_fuente) a.*
    FROM tenis.jugador_alias a
    WHERE a.recibido_en <= p_corte
      AND NOT EXISTS (SELECT 1 FROM tenis.jugador_alias x
                      WHERE x.anula_a = a.alias_id AND x.recibido_en <= p_corte)
    ORDER BY a.fuente, a.id_fuente, a.recibido_en DESC, a.alias_id DESC
$$;

-- Partido: una fila por partido_id, visible según recepción y regla RETRO.
CREATE OR REPLACE FUNCTION tenis.partido_a_las(p_corte TIMESTAMPTZ) RETURNS SETOF tenis.partido
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = tenis, pg_temp AS $$
    SELECT p.*
    FROM tenis.partido p
    JOIN tenis.recibo r ON r.recibo_id = p.recibo_id
    LEFT JOIN tenis.lunes_por_partido_a_las(p_corte) lp ON lp.partido_id = p.partido_id
    WHERE p.recibido_en <= p_corte
      AND tenis.retro_visible(p_corte, r.retro, lp.lunes_semana)
$$;

-- Horario vigente por partido: prioridad de calendario, luego el más reciente.
CREATE OR REPLACE FUNCTION tenis.programa_a_las(p_corte TIMESTAMPTZ) RETURNS SETOF tenis.programa
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = tenis, pg_temp AS $$
    SELECT DISTINCT ON (x.partido_id) x.*
    FROM tenis.programa x
    JOIN tenis.fuente f ON f.fuente = x.fuente
    JOIN tenis.recibo r ON r.recibo_id = x.recibo_id
    LEFT JOIN tenis.lunes_por_partido_a_las(p_corte) lp ON lp.partido_id = x.partido_id
    WHERE x.recibido_en <= p_corte
      AND tenis.retro_visible(p_corte, r.retro, lp.lunes_semana)
    ORDER BY x.partido_id, f.prioridad_calendario, x.recibido_en DESC, x.programa_id DESC
$$;

-- Desenlace vigente por partido: prioridad de resultado, luego el más reciente.
CREATE OR REPLACE FUNCTION tenis.resultado_a_las(p_corte TIMESTAMPTZ) RETURNS SETOF tenis.resultado
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = tenis, pg_temp AS $$
    SELECT DISTINCT ON (x.partido_id) x.*
    FROM tenis.resultado x
    JOIN tenis.fuente f ON f.fuente = x.fuente
    JOIN tenis.recibo r ON r.recibo_id = x.recibo_id
    LEFT JOIN tenis.lunes_por_partido_a_las(p_corte) lp ON lp.partido_id = x.partido_id
    WHERE x.recibido_en <= p_corte
      AND tenis.retro_visible(p_corte, r.retro, lp.lunes_semana)
    ORDER BY x.partido_id, f.prioridad_resultado, x.recibido_en DESC, x.resultado_id DESC
$$;

-- Estadística vigente por (partido, lado).
CREATE OR REPLACE FUNCTION tenis.estadistica_a_las(p_corte TIMESTAMPTZ) RETURNS SETOF tenis.estadistica
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = tenis, pg_temp AS $$
    SELECT DISTINCT ON (x.partido_id, x.lado) x.*
    FROM tenis.estadistica x
    JOIN tenis.fuente f ON f.fuente = x.fuente
    JOIN tenis.recibo r ON r.recibo_id = x.recibo_id
    LEFT JOIN tenis.lunes_por_partido_a_las(p_corte) lp ON lp.partido_id = x.partido_id
    WHERE x.recibido_en <= p_corte
      AND tenis.retro_visible(p_corte, r.retro, lp.lunes_semana)
    ORDER BY x.partido_id, x.lado, f.prioridad_resultado, x.recibido_en DESC, x.estadistica_id DESC
$$;

-- Ranking vigente por jugador. Con `p_fecha_partido` solo cuentan lunes <= esa fecha local (plan §C.4):
-- se toma, por jugador, la publicación más reciente que cumpla ambas condiciones.
CREATE OR REPLACE FUNCTION tenis.ranking_a_las(p_corte TIMESTAMPTZ, p_fecha_partido DATE DEFAULT NULL)
RETURNS SETOF tenis.ranking
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = tenis, pg_temp AS $$
    SELECT DISTINCT ON (v.circuito, v.jugador_id) v.*
    FROM (
        SELECT DISTINCT ON (x.circuito, x.jugador_id, x.fecha_publicacion) x.*
        FROM tenis.ranking x
        JOIN tenis.fuente f ON f.fuente = x.fuente
        JOIN tenis.recibo r ON r.recibo_id = x.recibo_id
        WHERE x.recibido_en <= p_corte
          AND tenis.retro_visible(p_corte, r.retro, x.fecha_publicacion)
        ORDER BY x.circuito, x.jugador_id, x.fecha_publicacion, f.prioridad_resultado,
                 x.recibido_en DESC, x.ranking_id DESC
    ) v
    WHERE p_fecha_partido IS NULL OR v.fecha_publicacion <= p_fecha_partido
    ORDER BY v.circuito, v.jugador_id, v.fecha_publicacion DESC
$$;
