"""SELECT de cajas de jugadores para validación/entrenamiento LOCAL; conserva recepción de la exportación."""
from pathlib import Path
import gzip
import json
import os
import sys

import psycopg

CONSULTA = """
WITH elegido AS (
 SELECT DISTINCT ON(d.partido_id, j.canonica_id,m.nombre)
        d.partido_id,j.canonica_id jugador,m.nombre,d.valor,d.recibido_en
 FROM nba.dato d JOIN nba.metrica m USING(metrica_id) JOIN nba.fuente f USING(fuente)
 JOIN nba.entidad j ON j.entidad_id=d.entidad_id AND j.tipo='jugador'
 JOIN nba.entidad g ON g.entidad_id=d.partido_id AND g.canonica_id=g.entidad_id
 WHERE d.fase='final' AND d.periodo=0 AND d.recibido_en<=%(corte)s
   AND m.nombre IN('minutos','equipo_del_jugador','mas_menos')
   AND NOT EXISTS(SELECT 1 FROM nba.captura c WHERE c.captura_id=d.captura_id
                  AND (c.recibido_en IS NULL OR c.recibido_en>%(corte)s))
 ORDER BY d.partido_id,j.canonica_id,m.nombre,f.prioridad,d.recibido_en DESC,d.dato_id DESC
), caja AS (
 SELECT partido_id,jugador,max(valor) FILTER(WHERE nombre='minutos') minutos,
        max(valor) FILTER(WHERE nombre='equipo_del_jugador')::bigint equipo,
        max(valor) FILTER(WHERE nombre='mas_menos') mas_menos,max(recibido_en) recibido
 FROM elegido GROUP BY partido_id,jugador
)
SELECT c.partido_id,c.jugador,t.id_en_fuente,c.minutos,c.mas_menos,c.recibido
FROM caja c JOIN nba.entidad t ON t.entidad_id=c.equipo
WHERE c.minutos>0 AND c.minutos<=60
ORDER BY c.partido_id,c.jugador
"""


def exportar(db, destino):
    with db.transaction():
        db.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        corte=db.execute('SELECT clock_timestamp()').fetchone()[0]
        filas=db.execute(CONSULTA,{'corte':corte}).fetchall()
    with gzip.open(destino,'xt',encoding='utf8') as f:
        json.dump(dict(captured_at_utc=corte.isoformat(),query=CONSULTA,rows=filas),f,default=lambda x:x.isoformat())
    return len(filas)


if __name__=='__main__':
    with psycopg.connect(os.environ['NBA_DB_DSN_LECTOR']) as db:
        print(json.dumps({'filas':exportar(db,Path(sys.argv[1]))}))
