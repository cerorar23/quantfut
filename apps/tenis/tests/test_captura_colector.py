"""ops/colector.sh: candado flock, log por fuente, código de salida y ausencia de secretos en la salida.

Se salta si no hay bash y flock (Windows no tiene flock: en CI Linux se ejercita).
"""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "ops" / "colector.sh"
SIN_FLOCK = shutil.which("bash") is None or shutil.which("flock") is None or sys.platform == "win32"
pytestmark = pytest.mark.skipif(SIN_FLOCK, reason="requiere bash y flock (Linux); no probado en Windows")


def _entorno(tmp_path, **extra):
    env = {k: v for k, v in os.environ.items()}
    env.update({"TENIS_LOCK_DIR": str(tmp_path / "locks"), "TENIS_LOG_DIR": str(tmp_path / "logs")})
    (tmp_path / "locks").mkdir(exist_ok=True)
    env.update(extra)
    return env


def _ejecutar(tmp_path, *args, **extra):
    return subprocess.run(["bash", str(SCRIPT), *args], env=_entorno(tmp_path, **extra),
                          capture_output=True, text=True, timeout=60)


def test_sintaxis_bash_valida():
    subprocess.run(["bash", "-n", str(SCRIPT)], check=True, timeout=30)


def test_comando_ok_registra_inicio_y_fin(tmp_path):
    r = _ejecutar(tmp_path, "sportsapipro", "true")
    assert r.returncode == 0
    log = (tmp_path / "logs" / "sportsapipro.log").read_text(encoding="utf-8")
    assert "fuente=sportsapipro inicio" in log and "fin codigo=0" in log


def test_codigo_de_salida_del_comando_se_propaga(tmp_path):
    r = _ejecutar(tmp_path, "sportsapipro", "bash", "-c", "exit 7")
    assert r.returncode == 7
    assert "fin codigo=7" in (tmp_path / "logs" / "sportsapipro.log").read_text(encoding="utf-8")


def test_candado_ocupado_sale_con_cero_sin_ejecutar(tmp_path):
    lock = tmp_path / "locks" / "tenis-sportsapipro.lock"
    (tmp_path / "locks").mkdir(exist_ok=True)
    marca = tmp_path / "ejecutado.txt"
    tenedor = subprocess.Popen(["flock", "-x", str(lock), "sleep", "30"])
    try:
        r = None
        for _ in range(50):  # esperar a que el tenedor tenga el candado
            r = _ejecutar(tmp_path, "sportsapipro", "bash", "-c", f"touch {marca}")
            if "ocupado" in r.stdout:
                break
            time.sleep(0.1)
        assert r is not None and r.returncode == 0 and "ocupado" in r.stdout
        assert not marca.exists()
        assert "ocupado" in (tmp_path / "logs" / "sportsapipro.log").read_text(encoding="utf-8")
    finally:
        tenedor.kill()
        tenedor.wait()
    r = _ejecutar(tmp_path, "sportsapipro", "bash", "-c", f"touch {marca}")
    assert r.returncode == 0 and marca.exists()


def test_fuente_invalida_o_sin_comando_da_error_de_uso(tmp_path):
    assert _ejecutar(tmp_path, "Sports API").returncode == 2
    assert _ejecutar(tmp_path, "sportsapipro").returncode == 2


def test_no_imprime_ni_registra_variables_de_entorno(tmp_path):
    secreto = "valor-secreto-de-prueba-9f3a"
    r = _ejecutar(tmp_path, "sportsapipro", "true", SPORTSAPIPRO_KEY=secreto)
    log = (tmp_path / "logs" / "sportsapipro.log").read_text(encoding="utf-8")
    assert secreto not in r.stdout + r.stderr + log
