-- 0006: métricas del parte oficial de lesiones y del final del partido (box score de cdn.nba.com).
INSERT INTO nba.metrica (metrica_id, nombre, nivel, unidad, definicion, resolucion, es_proyeccion) VALUES
    (57, 'motivo_disponibilidad', 'jugador', NULL, 'etiqueta = motivo textual del parte (p. ej. «Injury/Illness - Left Knee; Soreness»)', 'por_fuente', false),
    (58, 'reporte_no_enviado', 'equipo', 'bool', '1 si el equipo aparece como «NOT YET SUBMITTED» en el parte: no es lo mismo que no tener lesionados', 'por_fuente', false),
    (59, 'jugo', 'jugador', 'bool', '1 si el jugador entró a la cancha, 0 si estaba en la lista del partido y no jugó (box score final)', 'prioridad', false);
