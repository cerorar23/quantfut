-- La publicación de un parte reconstruido no acredita recepción del original.
-- Conserva todas las filas inmutables; refuerza únicamente su visibilidad temporal.
CREATE OR REPLACE FUNCTION nba.dato_a_las(corte timestamptz) RETURNS SETOF nba.dato
LANGUAGE sql STABLE AS $$
    SELECT v.* FROM (
        SELECT DISTINCT ON (d.partido_id, d.entidad_id, d.periodo, d.metrica_id, d.fase,
                            CASE WHEN m.resolucion = 'por_fuente' THEN d.fuente ELSE '' END)
               d.*
        FROM nba.dato d
        JOIN nba.metrica m ON m.metrica_id = d.metrica_id
        JOIN nba.fuente f ON f.fuente = d.fuente
        WHERE d.recibido_en <= corte
          AND NOT EXISTS (SELECT 1 FROM nba.captura c WHERE c.captura_id = d.captura_id
                          AND (c.recibido_en IS NULL OR c.recibido_en > corte))
        ORDER BY d.partido_id, d.entidad_id, d.periodo, d.metrica_id, d.fase,
                 CASE WHEN m.resolucion = 'por_fuente' THEN d.fuente ELSE '' END,
                 CASE WHEN m.resolucion = 'prioridad' THEN f.prioridad ELSE 0 END,
                 d.recibido_en DESC, d.dato_id DESC
    ) v
$$;
