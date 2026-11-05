"""Exporta SELECT a un archivo local nuevo usando NBA_DB_DSN_LECTOR; no entrena ni publica."""
from datetime import datetime, UTC
import json
import os
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

import psycopg

CONSULTA = """
WITH juegos AS (
 SELECT e.entidad_id,e.fecha_juego_et,e.temporada,(e.atributos->>'local')::bigint lo,(e.atributos->>'visitante')::bigint vi
 FROM nba.entidad e WHERE e.tipo='partido' AND e.canonica_id=e.entidad_id AND e.fecha_juego_et < %(fecha)s
), elegido AS (
 SELECT DISTINCT ON (d.partido_id,d.entidad_id,m.nombre) d.partido_id,d.entidad_id,m.nombre,d.valor,d.recibido_en
 FROM juegos j JOIN nba.dato d ON d.partido_id=j.entidad_id AND d.entidad_id IN(j.lo,j.vi)
 JOIN nba.metrica m USING(metrica_id) JOIN nba.fuente f USING(fuente)
 WHERE d.fase='final' AND d.periodo=0 AND d.recibido_en<=%(corte)s
 AND m.nombre IN('puntos','posesiones','minutos','tiros_campo_intentados','tiros_libres_intentados','rebotes_ofensivos','perdidas')
 ORDER BY d.partido_id,d.entidad_id,m.nombre,f.prioridad,d.recibido_en DESC,d.dato_id DESC
), lados AS (
 SELECT partido_id,entidad_id,jsonb_object_agg(nombre,valor) valores,max(recibido_en) recibido_en
 FROM elegido GROUP BY partido_id,entidad_id
)
SELECT j.entidad_id,j.fecha_juego_et,j.temporada,tl.id_en_fuente,tv.id_en_fuente,l.valores,v.valores,l.recibido_en,v.recibido_en
FROM juegos j JOIN nba.entidad tl ON tl.entidad_id=j.lo JOIN nba.entidad tv ON tv.entidad_id=j.vi
JOIN lados l ON l.partido_id=j.entidad_id AND l.entidad_id=j.lo
JOIN lados v ON v.partido_id=j.entidad_id AND v.entidad_id=j.vi
WHERE l.valores ? 'puntos' AND v.valores ? 'puntos'
ORDER BY j.fecha_juego_et,j.entidad_id
"""


def exportar(db, destino):
    with db.transaction():
        db.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        corte = db.execute('SELECT clock_timestamp()').fetchone()[0]
        filas = db.execute(CONSULTA, {'corte':corte,'fecha':corte.astimezone(ZoneInfo('America/New_York')).date()}).fetchall()
    # Exclusivo: no pisa una exportación ni muestra credenciales.
    with destino.open('x', encoding='utf8') as f:
        json.dump(dict(captured_at_utc=corte.isoformat(),query=CONSULTA,rows=filas),f,default=lambda x:x.isoformat())
    return len(filas)


if __name__ == '__main__':
    with psycopg.connect(os.environ['NBA_DB_DSN_LECTOR']) as db:
        print(json.dumps({'partidos':exportar(db,Path(sys.argv[1]))}))
