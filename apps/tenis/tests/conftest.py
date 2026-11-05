"""Fixtures de las pruebas de base de tenis. Usan QF_TEST_PG_DSN; sin él, las pruebas se omiten."""
import os
import uuid
from dataclasses import dataclass

import pytest

psycopg = pytest.importorskip("psycopg")
from psycopg import sql  # noqa: E402

from db_util import MIGRACIONES, sql_de  # noqa: E402


@dataclass(frozen=True)
class Esquema:
    dsn: str
    nombre: str
    nombre_op: str

    def conectar(self):
        """Conexión en autocommit con el esquema de prueba como search_path (los errores no envenenan la sesión)."""
        db = psycopg.connect(self.dsn, autocommit=True)
        db.execute(f"SET search_path TO {self.nombre}, public")
        return db


@pytest.fixture
def dsn():
    valor = os.environ.get("QF_TEST_PG_DSN")
    if not valor:
        pytest.skip("QF_TEST_PG_DSN ausente")
    return valor


@pytest.fixture
def esquema(dsn):
    """Esquema aislado con las migraciones de evidencia aplicadas (sin 0005: los roles tienen prueba propia)."""
    sufijo = uuid.uuid4().hex[:10]
    e = Esquema(dsn, f"tenis_t_{sufijo}", f"tenis_t_{sufijo}_op")
    with psycopg.connect(dsn, autocommit=True) as db:
        for nombre in MIGRACIONES:
            db.execute(sql_de(nombre, e.nombre, e.nombre_op))
    try:
        yield e
    finally:
        with psycopg.connect(dsn, autocommit=True) as db:
            db.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(e.nombre)))
            db.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(e.nombre_op)))
