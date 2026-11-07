"""Roles (0005/0006): el motor no lee tablas de evidencia, la captura no modifica, la lectura no escribe.

Se salta si el usuario de la prueba no puede crear roles, si es superusuario (ignora los permisos) o si no
puede hacer SET ROLE a los roles de grupo. Los roles son globales del clúster: quedan creados (NOLOGIN).
"""
import pytest

psycopg = pytest.importorskip("psycopg")
from psycopg import sql  # noqa: E402

from db_util import MIGRACION_ROLES, cargar_minimo, nuevo_recibo, sql_de, ts  # noqa: E402


@pytest.fixture
def roles_aplicados(dsn, esquema):
    with psycopg.connect(dsn, autocommit=True) as admin:
        atributos = admin.execute("SELECT rolcreaterole, rolsuper FROM pg_roles WHERE rolname = current_user").fetchone()
        if atributos is None or atributos[1]:
            pytest.skip("el usuario de prueba es superusuario (ignora permisos) o no existe en pg_roles")
        if not atributos[0]:
            pytest.skip("el usuario de prueba no puede crear roles")
        admin.execute(sql_de(MIGRACION_ROLES, esquema.nombre, esquema.nombre_op))
        # 0006 se vuelve a aplicar: ahora que existen los roles, concede lo que antes se omitió (idempotente).
        admin.execute(sql_de("0006_sellado.sql", esquema.nombre, esquema.nombre_op))
    return esquema


def como_rol(db, rol):
    try:
        db.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(rol)))
    except psycopg.errors.InsufficientPrivilege:
        pytest.skip(f"sin membresía para asumir {rol}")


def test_captura_inserta_pero_no_modifica_evidencia(roles_aplicados):
    e = roles_aplicados
    with e.conectar() as db:
        cargar_minimo(db)
        como_rol(db, "tenis_captura")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            db.execute(f"UPDATE {e.nombre}.partido SET ronda = 'X' WHERE false")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            db.execute(f"DELETE FROM {e.nombre}.partido WHERE false")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            db.execute(f"SELECT count(*) FROM {e.nombre}.partido")  # captura no lee la evidencia que escribe
        db.execute("RESET ROLE")


def test_motor_solo_usa_funciones_de_lectura_y_sellado(roles_aplicados):
    e = roles_aplicados
    with e.conectar() as db:
        m = cargar_minimo(db)
        como_rol(db, "tenis_motor")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            db.execute(f"SELECT count(*) FROM {e.nombre}.resultado")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            db.execute(f"INSERT INTO {e.nombre}.pronostico (partido_id, version_modelo, version_datos, corte, sellado_en, "
                       "entradas, distribucion, hash_previo, hash) VALUES (1, 'x', 'y', now(), now(), '{{}}', '{{}}', "
                       "'0', '0')")
        visibles = db.execute("SELECT count(*) FROM partido_a_las(%s)", (ts("2026-06-01"),)).fetchone()[0]
        assert visibles == 1
        assert m["partido"] > 0
        db.execute("RESET ROLE")


def test_lectura_no_escribe(roles_aplicados):
    e = roles_aplicados
    with e.conectar() as db:
        cargar_minimo(db)
        como_rol(db, "tenis_lectura")
        assert db.execute(f"SELECT count(*) FROM {e.nombre}.partido").fetchone()[0] == 1
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            db.execute(f"INSERT INTO {e.nombre}.recibo (fuente, recurso, recibido_en, sha256, ruta_objeto, bytes, lote) "
                       "VALUES ('tml', 'x', now(), repeat('a', 64), 'objetos/aa/" + "a" * 64 + ".json.gz', 1, 'x')")
        db.execute("RESET ROLE")
        assert nuevo_recibo(db) > 0
