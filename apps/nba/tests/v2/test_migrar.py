from pathlib import Path

import psycopg
import pytest

from nba.v2 import migrar


def test_conectar_rechaza_bases_ajenas():
    with pytest.raises(ValueError):
        migrar.conectar("dbname=quantfut")
    with pytest.raises(ValueError):
        migrar.conectar("")


def carpeta(tmp_path: Path, **archivos: str) -> Path:
    for nombre, texto in archivos.items():
        (tmp_path / f"{nombre}.sql").write_text(texto, encoding="utf-8", newline="\n")
    return tmp_path


def test_aplicar_es_idempotente(base_nueva, tmp_path):
    d = carpeta(tmp_path, **{"0001_a": "CREATE TABLE ta(x int);", "0002_b": "CREATE TABLE tb(x int);"})
    assert migrar.aplicar(base_nueva, d) == ["0001_a", "0002_b"]
    assert migrar.aplicar(base_nueva, d) == []


def test_aplicar_detecta_archivo_modificado(base_nueva, tmp_path):
    d = carpeta(tmp_path, **{"0001_a": "CREATE TABLE ta(x int);"})
    migrar.aplicar(base_nueva, d)
    (d / "0001_a.sql").write_text("CREATE TABLE ta(x int, y int);", encoding="utf-8", newline="\n")
    with pytest.raises(RuntimeError, match="0001_a"):
        migrar.aplicar(base_nueva, d)


def test_aplicar_en_orden_y_atomico(base_nueva, tmp_path):
    d = carpeta(tmp_path, **{"0001_a": "CREATE TABLE ta(x int);",
                             "0002_mala": "CREATE TABLE tb(x int); SELECT 1/0;"})
    with pytest.raises(psycopg.errors.DivisionByZero):
        migrar.aplicar(base_nueva, d)
    with psycopg.connect(base_nueva) as db:
        assert db.execute("SELECT to_regclass('ta')").fetchone()[0] is not None
        assert db.execute("SELECT to_regclass('tb')").fetchone()[0] is None
        versiones = [r[0] for r in db.execute("SELECT version FROM nba.migracion ORDER BY version")]
    assert versiones == ["0001_a"]
