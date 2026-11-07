"""Sellado de pronósticos (0006): cadena de hashes, UNIQUE, G-tiempo y recálculo independiente en Python."""
import pytest

psycopg = pytest.importorskip("psycopg")
from psycopg.types.json import Jsonb  # noqa: E402

from db_util import cargar_minimo, hash_esperado, insertar, sellar, ts  # noqa: E402

GENESIS = "0" * 64


def partido_futuro(db, m, inicio="2099-06-01T10:00:00Z", ronda="QF"):
    """Partido nuevo con horario programado (fijo, en el futuro) y cuatro jugadores de la prueba."""
    r = db.execute("SELECT recibo_id FROM recibo LIMIT 1").fetchone()[0]
    a, b = m["jugadores"][0], m["jugadores"][1]
    p = insertar(db, "INSERT INTO partido (edicion_id, ronda, jugador_1, jugador_2, mejor_de, fuente, recibo_id, "
                     "recibido_en) VALUES (%s, %s, %s, %s, 3, 'sofascore', %s, %s) RETURNING partido_id",
                 (m["edicion"], ronda, a, b, r, ts("2026-01-05")))
    db.execute("INSERT INTO programa (partido_id, inicio_programado_utc, tipo_hora, estado, fuente, recibo_id, recibido_en) "
               "VALUES (%s, %s, 'fija', 'programado', 'sofascore', %s, %s)", (p, ts(inicio), r, ts("2026-01-05")))
    return p


def filas_sellos(db):
    return db.execute("SELECT pronostico_id, partido_id, version_modelo, version_datos, corte, sellado_en, entradas, "
                      "distribucion, referencia_mercado, hash_previo, hash FROM pronostico ORDER BY pronostico_id").fetchall()


COLUMNAS = ["pronostico_id", "partido_id", "version_modelo", "version_datos", "corte", "sellado_en", "entradas",
            "distribucion", "referencia_mercado", "hash_previo", "hash"]


def test_cadena_de_hashes_y_recalculo_independiente(esquema):
    with esquema.conectar() as db:
        m = cargar_minimo(db)              # ya contiene un sello (el primero de la cadena)
        p2 = partido_futuro(db, m, ronda="QF")
        p3 = partido_futuro(db, m, ronda="SF")
        h2 = sellar(db, p2, "v1", ts("2026-01-06"), entradas={"x": 1.5}, distribucion={"p_1": 0.25, "p_2": 0.75})
        h3 = sellar(db, p3, "v1", ts("2026-01-07"), entradas={"x": 2}, distribucion={"p_1": 0.5})
        filas = [dict(zip(COLUMNAS, f)) for f in filas_sellos(db)]
        assert len(filas) == 3
        assert filas[0]["hash_previo"] == GENESIS
        for previo, actual in zip(filas, filas[1:]):
            assert actual["hash_previo"] == previo["hash"]
        # Recalculo independiente: la huella de cada fila debe salir de sus columnas con la serialización documentada.
        previo = GENESIS
        for fila in filas:
            assert hash_esperado(fila, previo) == fila["hash"]
            previo = fila["hash"]
        assert filas[1]["hash"] == h2 and filas[2]["hash"] == h3


def test_sellar_dos_veces_lo_mismo_se_rechaza(esquema):
    with esquema.conectar() as db:
        m = cargar_minimo(db)
        p = partido_futuro(db, m)
        sellar(db, p, "v2", ts("2026-01-06"))
        with pytest.raises(psycopg.errors.UniqueViolation):
            sellar(db, p, "v2", ts("2026-01-06"))
        assert db.execute("SELECT count(*) FROM pronostico WHERE partido_id = %s", (p,)).fetchone()[0] == 1


def test_no_se_sella_despues_del_inicio_programado(esquema):
    with esquema.conectar() as db:
        m = cargar_minimo(db)
        pasado = partido_futuro(db, m, inicio="2020-01-01T10:00:00Z", ronda="R16")
        with pytest.raises(psycopg.Error, match="tardio"):
            sellar(db, pasado, "v1", ts("2019-12-31"))


def test_no_se_sella_sin_inicio_programado_conocido(esquema):
    with esquema.conectar() as db:
        m = cargar_minimo(db)
        r = db.execute("SELECT recibo_id FROM recibo LIMIT 1").fetchone()[0]
        sin = insertar(db, "INSERT INTO partido (edicion_id, ronda, jugador_1, jugador_2, mejor_de, fuente, recibo_id, "
                           "recibido_en) VALUES (%s, 'R128', %s, %s, 3, 'sofascore', %s, %s) RETURNING partido_id",
                       (m["edicion"], m["jugadores"][0], m["jugadores"][1], r, ts("2026-01-05")))
        with pytest.raises(psycopg.Error, match="sin inicio programado"):
            sellar(db, sin, "v1", ts("2026-01-06"))


def test_no_se_sella_con_datos_del_futuro(esquema):
    with esquema.conectar() as db:
        m = cargar_minimo(db)
        p = partido_futuro(db, m)
        with pytest.raises(psycopg.Error, match="futuro"):
            sellar(db, p, "v1", ts("2099-01-02"))
        # La restricción de tabla lo impediría igualmente si la función se saltara.
        assert db.execute("SELECT count(*) FROM pronostico WHERE partido_id = %s", (p,)).fetchone()[0] == 0


def test_un_sello_no_se_altera_ni_borra(esquema):
    with esquema.conectar() as db:
        cargar_minimo(db)
        with pytest.raises(psycopg.Error, match="inmutable"):
            db.execute("UPDATE pronostico SET version_modelo = 'otra'")
        with pytest.raises(psycopg.Error, match="inmutable"):
            db.execute("DELETE FROM pronostico WHERE false")


def test_json_canonico_coincide_con_la_reproduccion_python(esquema):
    from db_util import _canon  # noqa: PLC0415
    with esquema.conectar() as db:
        valor = {"b": [1, 0.25, None, True], "a": {"z": "ñ", "y": 2}}
        sql_txt = db.execute("SELECT json_canonico(%s)", (Jsonb(valor),)).fetchone()[0]
        assert sql_txt == _canon(valor)
