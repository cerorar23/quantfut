"""Inmutabilidad (0003) y restricciones (CHECK/UNIQUE) del esquema tenis. Requiere QF_TEST_PG_DSN."""
import pytest

psycopg = pytest.importorskip("psycopg")
from psycopg.types.json import Jsonb  # noqa: E402

from db_util import TABLAS_EVIDENCIA_ESPERADAS, cargar_minimo, insertar, nuevo_recibo, ts  # noqa: E402


def tablas_de(db, esquema_nombre):
    return [f[0] for f in db.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname = %s ORDER BY tablename", (esquema_nombre,)).fetchall()]


def test_todas_las_tablas_de_evidencia_son_inmutables(esquema):
    with esquema.conectar() as db:
        mundo = cargar_minimo(db)
        tablas = tablas_de(db, esquema.nombre)
        assert TABLAS_EVIDENCIA_ESPERADAS <= set(tablas), "falta alguna tabla de evidencia en el catálogo"
        for t in tablas:
            # Una columna que no sea identidad (UPDATE SET id = id falla antes de llegar al disparador).
            columna = db.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema = %s AND table_name = %s "
                "AND is_identity = 'NO' ORDER BY ordinal_position LIMIT 1", (esquema.nombre, t)).fetchone()[0]
            # Sentencias que no afectan a ninguna fila: el disparador por sentencia debe fallar igual.
            with pytest.raises(psycopg.Error, match="inmutable"):
                db.execute(f'DELETE FROM {t} WHERE false')
            with pytest.raises(psycopg.Error, match="inmutable"):
                db.execute(f'UPDATE {t} SET "{columna}" = "{columna}" WHERE false')
            with pytest.raises(psycopg.Error, match="inmutable"):
                db.execute(f'TRUNCATE {t} CASCADE')
        # Los datos siguen ahí tras todos los intentos.
        assert db.execute("SELECT count(*) FROM partido").fetchone()[0] == 1
        assert mundo["partido"] > 0


def test_el_estado_operativo_no_es_evidencia(esquema):
    with esquema.conectar() as db:
        cargar_minimo(db)
        db.execute(f"INSERT INTO {esquema.nombre_op}.presupuesto (fuente, dia, tope, usadas) "
                   "VALUES ('sofascore', '2026-11-05', 100, 3)")
        db.execute(f"UPDATE {esquema.nombre_op}.presupuesto SET usadas = 4 WHERE fuente = 'sofascore'")
        db.execute(f"DELETE FROM {esquema.nombre_op}.presupuesto WHERE fuente = 'sofascore'")
        assert db.execute(f"SELECT count(*) FROM {esquema.nombre_op}.presupuesto").fetchone()[0] == 0


def test_partido_rechaza_orden_no_canonico_y_formato_invalido(esquema):
    with esquema.conectar() as db:
        m = cargar_minimo(db)
        a, b = m["jugadores"][0], m["jugadores"][1]
        r = nuevo_recibo(db)
        base = ("INSERT INTO partido (edicion_id, ronda, jugador_1, jugador_2, mejor_de, fuente, recibo_id, recibido_en) "
                "VALUES (%s, 'SF', %s, %s, %s, 'sofascore', %s, %s)")
        casos = {
            "jugador_1 = jugador_2": (m["edicion"], a, a, 3),
            "jugador_1 > jugador_2 (ganador primero)": (m["edicion"], b, a, 3),
            "mejor_de = 4": (m["edicion"], a, b, 4),
        }
        for nombre, (ed, j1, j2, bo) in casos.items():
            with pytest.raises(psycopg.errors.CheckViolation):
                db.execute(base, (ed, j1, j2, bo, r, ts("2026-01-05")))
            assert nombre


def test_resultado_y_estadistica_rechazan_valores_imposibles(esquema):
    with esquema.conectar() as db:
        m = cargar_minimo(db)
        p = m["partido"]
        r = nuevo_recibo(db)
        # Partido ya tiene resultado (UNIQUE); se prueban filas de otros recibos/fechas para llegar al CHECK.
        with pytest.raises(psycopg.errors.CheckViolation):
            db.execute("INSERT INTO resultado (partido_id, estado, ganador, sets, sets_completos, duracion_min, fuente, "
                       "recibo_id, recibido_en) VALUES (%s, 'completado', 1, %s, 2, 0, 'sofascore', %s, %s)",
                       (p, Jsonb([[6, 3, None, None], [6, 4, None, None]]), r, ts("2026-02-01")))
        with pytest.raises(psycopg.errors.CheckViolation):
            db.execute("INSERT INTO resultado (partido_id, estado, ganador, sets, sets_completos, duracion_min, fuente, "
                       "recibo_id, recibido_en) VALUES (%s, 'completado', 1, %s, 1, 90, 'sofascore', %s, %s)",
                       (p, Jsonb([[6, 1, None, None]]), r, ts("2026-02-01")))
        with pytest.raises(psycopg.errors.CheckViolation):
            db.execute("INSERT INTO resultado (partido_id, estado, ganador, sets_completos, fuente, recibo_id, recibido_en) "
                       "VALUES (%s, 'walkover', 1, NULL, 'sofascore', %s, %s)", (p, r, ts("2026-02-01")))
        with pytest.raises(psycopg.errors.CheckViolation):
            db.execute("INSERT INTO estadistica (partido_id, lado, primeros_dentro, primeros_ganados, puntos_saque, "
                       "fuente, recibo_id, recibido_en) VALUES (%s, 2, 30, 31, 60, 'sofascore', %s, %s)",
                       (p, r, ts("2026-02-01")))
        with pytest.raises(psycopg.errors.CheckViolation):
            db.execute("INSERT INTO estadistica (partido_id, lado, aces, fuente, recibo_id, recibido_en) "
                       "VALUES (%s, 2, -1, 'sofascore', %s, %s)", (p, r, ts("2026-02-01")))


def test_precio_edicion_y_ranking_rechazan_valores_imposibles(esquema):
    with esquema.conectar() as db:
        m = cargar_minimo(db)
        r = nuevo_recibo(db)
        with pytest.raises(psycopg.errors.CheckViolation):
            db.execute("INSERT INTO precio_mercado (recibo_id, evento_fuente, partido_id, casa, mercado, periodo, linea, "
                       "lado, cuota_decimal, clase_cierre, fuente, recibido_en) VALUES (%s, 'ev', %s, 'x', 'ganador', "
                       "'completo', NULL, '2', 1.000, 'b', 'tennis_data', %s)", (r, m["partido"], ts("2026-02-01")))
        with pytest.raises(psycopg.errors.CheckViolation):
            db.execute("INSERT INTO edicion (torneo_id, temporada, lunes_semana, superficie, fuente, recibo_id, recibido_en) "
                       "VALUES (%s, 2025, '2025-03-03', 'lava', 'sofascore', %s, %s)", (m["torneo"], r, ts("2026-02-01")))
        with pytest.raises(psycopg.errors.CheckViolation):
            db.execute("INSERT INTO ranking (circuito, fecha_publicacion, jugador_id, posicion, origen, fuente, recibo_id, "
                       "recibido_en) VALUES ('atp', '2026-03-02', %s, 0, 'oficial_capturado', 'sofascore', %s, %s)",
                       (m["jugadores"][0], r, ts("2026-02-01")))
        with pytest.raises(psycopg.errors.CheckViolation):
            db.execute("INSERT INTO ranking (circuito, fecha_publicacion, jugador_id, posicion, origen, fuente, recibo_id, "
                       "recibido_en) VALUES ('atp', '2026-03-03', %s, 1, 'oficial_capturado', 'sofascore', %s, %s)",
                       (m["jugadores"][0], r, ts("2026-02-01")))


def test_hashes_y_sha256_de_recibo_tienen_formato(esquema):
    with esquema.conectar() as db:
        cargar_minimo(db)
        with pytest.raises(psycopg.errors.CheckViolation):
            db.execute("INSERT INTO recibo (fuente, recurso, recibido_en, sha256, ruta_objeto, bytes, lote) "
                       "VALUES ('tml', 'x', %s, %s, %s, 1, 'x')",
                       (ts("2026-01-05"), "ABC", "objetos/AB/ABC.json.gz"))
        # Una ruta con prefijo Windows o distinta del hash se rechaza.
        h = "a" * 64
        with pytest.raises(psycopg.errors.CheckViolation):
            db.execute("INSERT INTO recibo (fuente, recurso, recibido_en, sha256, ruta_objeto, bytes, lote) "
                       "VALUES ('tml', 'x', %s, %s, %s, 1, 'x')",
                       (ts("2026-01-05"), h, "C:\\datos\\" + h + ".json.gz"))


def test_recibo_no_guarda_claves_en_parametros(esquema):
    with esquema.conectar() as db:
        cargar_minimo(db)
        h = "b" * 64
        with pytest.raises(psycopg.errors.CheckViolation):
            db.execute("INSERT INTO recibo (fuente, recurso, recibido_en, parametros, sha256, ruta_objeto, bytes, lote) "
                       "VALUES ('tml', 'x', %s, %s, %s, %s, 1, 'x')",
                       (ts("2026-01-05"), Jsonb({"api_key": "no"}), h, f"objetos/bb/{h}.json.gz"))


def test_clave_natural_de_torneo_es_unica(esquema):
    with esquema.conectar() as db:
        m = cargar_minimo(db)
        with pytest.raises(psycopg.errors.UniqueViolation):
            db.execute("INSERT INTO torneo (circuito, clave, nombre, fuente, recibo_id, recibido_en) "
                       "VALUES ('atp', 'roland-garros', 'Otro', 'sofascore', %s, %s)", (m["recibo"], ts("2026-01-05")))
        assert insertar(db, "SELECT count(*) FROM torneo") == 1


def test_edicion_exige_que_el_lunes_sea_el_de_la_semana_del_fin(esquema):
    """Un torneo de dos semanas con el lunes de INICIO abriría una fuga retro: la base lo rechaza."""
    import psycopg
    from db_util import cargar_minimo, nuevo_recibo, ts
    with esquema.conectar() as db:
        d = cargar_minimo(db)
        r = nuevo_recibo(db)
        sentencia = ("INSERT INTO edicion (torneo_id, temporada, lunes_semana, fecha_fin, fuente, recibo_id, recibido_en) "
                     "VALUES (%s, 2027, %s, %s, 'sofascore', %s, %s)")
        # Final un domingo 2027-03-14: su lunes es 2027-03-08. El lunes de inicio (2027-03-01) debe rechazarse.
        with pytest.raises(psycopg.errors.CheckViolation):
            db.execute(sentencia, (d["torneo"], "2027-03-01", "2027-03-14", r, ts("2027-01-05")))
        db.execute(sentencia, (d["torneo"], "2027-03-08", "2027-03-14", r, ts("2027-01-05")))
        # Final un lunes: ese mismo día es el lunes de la semana.
        db.execute(sentencia.replace("2027, %s", "2028, %s"), (d["torneo"], "2028-03-06", "2028-03-06", r, ts("2027-01-05")))
