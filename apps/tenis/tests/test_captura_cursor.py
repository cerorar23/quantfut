"""Cursor de colector (tenis_op.cursor): el avance va con el lote en una transacción; repetir no duplica."""
from datetime import datetime, timezone

import pytest

psycopg = pytest.importorskip("psycopg")

from tenis.captura import cursor as cu  # noqa: E402

from db_util import cargar_minimo, nuevo_recibo  # noqa: E402


def conexion(e):
    db = psycopg.connect(e.dsn, autocommit=True)
    db.execute(f"SET search_path TO {e.nombre}, {e.nombre_op}, public")
    return db


def _sin_resolver(db, rid, n):
    for i in range(n):
        db.execute("INSERT INTO sin_resolver (fuente, id_fuente, nombre_fuente, motivo, recibo_id, recibido_en) "
                   "VALUES ('sofascore', %s, 'X', 'prueba', %s, %s)",
                   (f"cur-{i}", rid, datetime(2026, 1, 5, tzinfo=timezone.utc)))


def _contar_sin(db):
    return db.execute("SELECT count(*) FROM sin_resolver WHERE motivo = 'prueba'").fetchone()[0]


def test_lote_correcto_avanza_el_cursor(esquema):
    with conexion(esquema) as db:
        cargar_minimo(db)
        rid = nuevo_recibo(db, "sofascore", "2026-01-05")

        def lote(conn, previo):
            assert previo is None
            _sin_resolver(conn, rid, 1)
            return "2026-11-02"

        assert cu.ejecutar_lote(db, "sofascore", "ranking_test", lote) == "2026-11-02"
        assert cu.leer(db, "sofascore", "ranking_test") == "2026-11-02"
        assert _contar_sin(db) == 1


def test_fallo_a_mitad_de_lote_deja_cursor_y_evidencia_igual(esquema):
    with conexion(esquema) as db:
        cargar_minimo(db)
        rid = nuevo_recibo(db, "sofascore", "2026-01-05")

        def lote_ok(conn, previo):
            _sin_resolver(conn, rid, 1)
            return "2026-11-02"

        cu.ejecutar_lote(db, "sofascore", "ranking_test", lote_ok)
        antes = _contar_sin(db)

        def lote_roto(conn, previo):
            _sin_resolver(conn, rid, 3)  # escribe y luego falla
            raise RuntimeError("fallo a mitad de lote")

        with pytest.raises(RuntimeError):
            cu.ejecutar_lote(db, "sofascore", "ranking_test", lote_roto)
        assert cu.leer(db, "sofascore", "ranking_test") == "2026-11-02"
        assert _contar_sin(db) == antes


def test_repetir_el_lote_no_duplica_filas(esquema):
    with conexion(esquema) as db:
        m = cargar_minimo(db)
        rid = nuevo_recibo(db, "sofascore", "2026-01-05")
        recibido = datetime(2026, 11, 2, 9, tzinfo=timezone.utc)

        def lote(conn, previo):
            conn.execute("INSERT INTO ranking (circuito, fecha_publicacion, jugador_id, posicion, puntos, origen, "
                         "fuente, recibo_id, recibido_en) VALUES ('atp', '2026-11-02', %s, 1, 9000, "
                         "'oficial_capturado', 'sofascore', %s, %s) ON CONFLICT DO NOTHING",
                         (m["jugadores"][0], rid, recibido))
            return "2026-11-02"

        cu.ejecutar_lote(db, "sofascore", "ranking_test", lote)
        cu.ejecutar_lote(db, "sofascore", "ranking_test", lote)
        n = db.execute("SELECT count(*) FROM ranking WHERE recibido_en = %s AND origen = 'oficial_capturado'",
                       (recibido,)).fetchone()[0]
        assert n == 1


def test_lote_que_no_avanza_devuelve_el_valor_previo(esquema):
    with conexion(esquema) as db:
        cargar_minimo(db)
        rid = nuevo_recibo(db, "sofascore", "2026-01-05")

        def lote_ok(conn, previo):
            _sin_resolver(conn, rid, 1)
            return "2026-11-02"

        cu.ejecutar_lote(db, "sofascore", "ranking_test", lote_ok)
        assert cu.ejecutar_lote(db, "sofascore", "ranking_test", lambda c, p: None) == "2026-11-02"
        assert cu.leer(db, "sofascore", "ranking_test") == "2026-11-02"
