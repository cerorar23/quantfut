-- 0004: único camino de lectura del motor (punto en el tiempo) y vistas de cuotas.
--
-- nba.dato_a_las(corte): lo que se sabía en `corte` (recibido_en <= corte, inclusivo).
--   métricas 'prioridad'  -> una fila por (partido, entidad, periodo, métrica, fase): gana la fuente de mejor
--                            prioridad; a igualdad, la más reciente; a igualdad, la de mayor dato_id.
--   métricas 'por_fuente' -> una fila por fuente: la más reciente visible.
CREATE FUNCTION nba.dato_a_las(corte timestamptz) RETURNS SETOF nba.dato
LANGUAGE sql STABLE AS $$
    SELECT v.* FROM (
        SELECT DISTINCT ON (d.partido_id, d.entidad_id, d.periodo, d.metrica_id, d.fase,
                            CASE WHEN m.resolucion = 'por_fuente' THEN d.fuente ELSE '' END)
               d.*
        FROM nba.dato d
        JOIN nba.metrica m ON m.metrica_id = d.metrica_id
        JOIN nba.fuente f ON f.fuente = d.fuente
        WHERE d.recibido_en <= corte
        ORDER BY d.partido_id, d.entidad_id, d.periodo, d.metrica_id, d.fase,
                 CASE WHEN m.resolucion = 'por_fuente' THEN d.fuente ELSE '' END,
                 CASE WHEN m.resolucion = 'prioridad' THEN f.prioridad ELSE 0 END,
                 d.recibido_en DESC, d.dato_id DESC
    ) v
$$;

CREATE VIEW nba.dato_vigente AS SELECT * FROM nba.dato_a_las(now());

CREATE VIEW nba.conflicto AS SELECT * FROM nba.dato WHERE conflicto;

-- Última cuota del cierre de cada contrato y lado.
CREATE VIEW nba.cuota_cierre AS
    SELECT DISTINCT ON (partido_id, fuente, casa, contrato_id, lado) *
    FROM nba.cuota
    WHERE fase = 'cierre'
    ORDER BY partido_id, fuente, casa, contrato_id, lado, recibido_en DESC, cuota_id DESC;

-- Margen implícito (suma de probabilidades - 1) del cierre; derivado, no se guarda.
CREATE VIEW nba.cuota_margen AS
    SELECT partido_id, fuente, casa, mercado, periodo, entidad_id, linea,
           count(*)::int AS n_lados, sum(1 / cuota) - 1 AS margen
    FROM nba.cuota_cierre
    GROUP BY partido_id, fuente, casa, mercado, periodo, entidad_id, linea;
