# apps/tenis/ops/medir_pit.py
"""Mide cuánto tarda la lectura punto en el tiempo (`resultado_a_las`) al crecer el número de partidos.

Crea un esquema aislado con datos sintéticos (generate_series), cronometra y lo borra. Solo lectura sobre el resto.
Uso:  QF_TEST_PG_DSN=... python medir_pit.py [N_PARTIDOS ...]   (por omisión 5000 10000 20000)
Es la medición que pidió el plan (K.2 S1) para decidir si la consulta escala hasta ~0,5 M de partidos.
"""
import os
import sys
import time
import uuid
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from db_util import MIGRACIONES, sql_de  # noqa: E402

EDICIONES = 600
JUGADORES = 2000


def crear(dsn, n_partidos):
    s = f"tenis_m_{uuid.uuid4().hex[:8]}"
    db = psycopg.connect(dsn, autocommit=True)
    db.execute(f"CREATE SCHEMA {s}")
    db.execute(f"CREATE SCHEMA {s}_op")
    db.execute(f"SET search_path TO {s}, public")
    for m in MIGRACIONES:
        db.execute(sql_de(m, s, s + "_op"))
    rid = db.execute(
        "INSERT INTO recibo (fuente, recurso, recibido_en, estado_http, sha256, ruta_objeto, bytes, lote, retro) "
        "VALUES ('tml', 'sintetico', '2026-10-17T01:00:00Z', 200, repeat('a', 64), "
        "'objetos/aa/' || repeat('a', 64) || '.json.gz', 1, 'sintetico', true) RETURNING recibo_id").fetchone()[0]
    db.execute("INSERT INTO torneo (circuito, clave, nombre, categoria, fuente, recibo_id, recibido_en) "
               "SELECT 'atp', 't' || g, 'Torneo ' || g, '250', 'tml', %s, '2026-10-17T01:00:00Z' "
               "FROM generate_series(1, %s) g", (rid, EDICIONES // 3))
    por_temporada = EDICIONES // 3
    db.execute("INSERT INTO edicion (torneo_id, temporada, lunes_semana, superficie, indoor, fuente, recibo_id, recibido_en) "
               "SELECT (SELECT min(torneo_id) FROM torneo) + ((g - 1) %% %s), 2020 + (g - 1) / %s, "
               "DATE '2020-01-06' + 7 * ((g * 5) %% 150), 'hard', false, 'tml', %s, '2026-10-17T01:00:00Z' "
               "FROM generate_series(1, %s) g", (por_temporada, por_temporada, rid, EDICIONES))
    db.execute("INSERT INTO jugador (circuito, recibo_id, recibido_en) SELECT 'atp', %s, '2026-10-17T01:00:00Z' "
               "FROM generate_series(1, %s)", (rid, JUGADORES))
    db.execute("INSERT INTO partido (edicion_id, ronda, jugador_1, jugador_2, mejor_de, fuente, recibo_id, recibido_en) "
               "SELECT (SELECT min(edicion_id) FROM edicion) + (i %% (SELECT count(*) FROM edicion)), 'R' || (i %% 5 + 1), "
               "(SELECT min(jugador_id) FROM jugador) + (i %% 1000), (SELECT min(jugador_id) FROM jugador) + 1000 + (i %% 997), "
               "3, 'tml', %s, '2026-10-17T01:00:00Z' FROM generate_series(1, %s) i", (rid, n_partidos))
    db.execute("INSERT INTO resultado (partido_id, estado, ganador, sets, sets_completos, fuente, recibo_id, recibido_en) "
               "SELECT partido_id, 'completado', 1, '[[6,3,null,null],[6,4,null,null]]'::jsonb, 2, 'tml', %s, "
               "'2026-10-17T01:00:00Z' FROM partido", (rid,))
    return db, s


def main():
    dsn = os.environ.get("QF_TEST_PG_DSN")
    if not dsn:
        sys.exit("falta QF_TEST_PG_DSN")
    tamanos = [int(x) for x in sys.argv[1:]] or [5000, 10000, 20000]
    for n in tamanos:
        db, s = crear(dsn, n)
        try:
            real = db.execute("SELECT count(*) FROM partido").fetchone()[0]
            ed = db.execute("SELECT count(*) FROM edicion").fetchone()[0]
            db.execute("SET statement_timeout = '300s'")
            t = time.perf_counter()
            filas = db.execute("SELECT count(*) FROM resultado_a_las('2026-11-05T00:00:00Z')").fetchone()[0]
            seg = time.perf_counter() - t
            print(f"partidos={real} ediciones={ed} resultado_a_las -> {filas} filas en {seg:.2f} s")
        finally:
            db.execute(f"DROP SCHEMA {s} CASCADE")
            db.execute(f"DROP SCHEMA {s}_op CASCADE")
            db.close()


if __name__ == "__main__":
    main()
