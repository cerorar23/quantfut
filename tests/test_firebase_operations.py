import importlib.util
import os
import time
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "firebase_operations", Path(__file__).resolve().parents[1] / "scripts" / "firebase_operations.py")
ops = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ops)


def make(directory: Path, name: str, days_old: float) -> Path:
    f = directory / name
    f.write_bytes(b"x")
    t = time.time() - days_old * 86400
    os.utime(f, (t, t))
    return f


def test_rotate_borra_solo_copias_comerciales_vencidas(tmp_path):
    vieja = make(tmp_path, "commercial-20260901T000000Z.dump", 31)
    vieja_json = make(tmp_path, "commercial-20260901T000000Z.json", 31)
    reciente = make(tmp_path, "commercial-20261010T000000Z.dump", 29)
    ajeno = make(tmp_path, "otra-cosa.dump", 400)
    parcial = make(tmp_path, "commercial-20260901T000000Z.partial", 400)
    assert sorted(ops.rotate(tmp_path)) == sorted([vieja.name, vieja_json.name])
    assert reciente.exists() and ajeno.exists() and parcial.exists()
    assert not vieja.exists() and not vieja_json.exists()


def test_rotate_ignora_enlaces_y_directorios(tmp_path):
    objetivo = make(tmp_path, "objetivo.txt", 400)
    enlace = tmp_path / "commercial-20260801T000000Z.dump"
    try:
        enlace.symlink_to(objetivo)
    except OSError:
        pytest.skip("sin permiso para crear enlaces simbolicos")
    (tmp_path / "commercial-dir.dump").mkdir()
    assert ops.rotate(tmp_path) == []
    assert objetivo.exists() and enlace.is_symlink()


def test_la_retencion_coincide_con_lo_publicado():
    # docs/legal/PRIVACIDAD_QUANTFUT.md promete 30 dias para las copias comerciales.
    assert ops.RETENTION_DAYS == 30
