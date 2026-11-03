-- 0008: a qué equipo jugó cada jugador en cada partido (la caja por jugador no lo traía como dato propio y no se deduce
-- sin ambigüedad). valor = entidad_id del equipo; imprescindible para armar plantillas, props y el impacto por jugador.
INSERT INTO nba.metrica (metrica_id, nombre, nivel, unidad, definicion, resolucion, es_proyeccion) VALUES
    (60, 'equipo_del_jugador', 'jugador', 'entidad_id', 'valor = entidad_id del equipo con el que el jugador figura en la caja de ese partido (también si no jugó)', 'prioridad', false);
