"""Pruebas de la base `nba_datos`: usan un Postgres desechable, nunca la base de fútbol."""
import os
import uuid
import json
from pathlib import Path

import pytest

pytest.importorskip("psycopg")
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo


@pytest.fixture(autouse=True)
def artefacto_sintetico(tmp_path, monkeypatch):
    """Estado sintético previo a las fechas de prueba, nunca el artefacto real del futuro."""
    from nba.v2.equipos import TRICODES
    a = dict(formato='nba-equipo-congelado-1', unidad_ratings='puntos_por_100_posesiones',
             objetivo_simulacion='regulacion_mas_prorroga', sigma_margen=14., sigma_total=18.,
             posesiones_referencia=100., efecto_b2b=2.9, partidos=500,
             ot={'intercepto':-2.6, 'abs_margen':-.04},
             conocido_en_utc='2025-12-01T00:00:00+00:00', datos_hasta='2025-11-30',
             vigencia_horas=20000, ataque={t: 0.0 for t in TRICODES}, defensa={t: 0.0 for t in TRICODES},
             ritmo={t: 100.0 for t in TRICODES}, liga=224.0, localia=2.6)
    ruta = tmp_path / 'equipo_sintetico.json'
    ruta.write_text(json.dumps(a), encoding='utf-8')
    monkeypatch.setenv('NBA_ESTADO_EQUIPO_JSON', str(ruta))


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
