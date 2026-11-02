"""Pruebas de la base `nba_datos`: usan un Postgres desechable, nunca la base de fútbol."""
import os
import uuid

import pytest

pytest.importorskip("psycopg")
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo


@pytest.fixture
def base_nueva():
    """DSN de una base `nba_test_<id>` recién creada en el clúster de NBA_TEST_PG_ADMIN_DSN."""
    admin = os.environ.get("NBA_TEST_PG_ADMIN_DSN")
    if not admin:
        pytest.skip("NBA_TEST_PG_ADMIN_DSN ausente (python apps/nba/ops/cluster_prueba.py start)")
    nombre = f"nba_test_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(admin, autocommit=True) as db:
        db.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(nombre)))
    try:
        yield make_conninfo(admin, dbname=nombre)
    finally:
        with psycopg.connect(admin, autocommit=True) as db:
            db.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(nombre)))


@pytest.fixture
def base_migrada(base_nueva):
    from nba.v2 import migrar
    migrar.aplicar(base_nueva)
    with psycopg.connect(base_nueva) as db:
        yield db
        db.rollback()


@pytest.fixture
def base_migrada_dsn(base_nueva):
    """DSN de una base ya migrada (para probar procesos que abren su propia conexión)."""
    from nba.v2 import migrar
    migrar.aplicar(base_nueva)
    return base_nueva
