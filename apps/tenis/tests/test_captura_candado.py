"""Candado por fuente entre procesos reales: el segundo sale como «ocupado» y el candado se libera al morir el primero."""
import subprocess
import sys
from pathlib import Path

from tenis.captura.candado import OCUPADO, Candado, intentar

SRC = str(Path(__file__).resolve().parents[1] / "src")
TENEDOR = (
    "import sys, time; sys.path.insert(0, {src!r}); from tenis.captura.candado import Candado; "
    "c = Candado({ruta!r}); assert c.tomar(); print('listo', flush=True); time.sleep(60)"
)


def _tenedor(ruta):
    codigo = TENEDOR.format(src=SRC, ruta=str(ruta))
    proc = subprocess.Popen([sys.executable, "-c", codigo], stdout=subprocess.PIPE, text=True)
    assert proc.stdout.readline().strip() == "listo"
    return proc


def test_mismo_proceso_no_toma_dos_veces(tmp_path):
    c1 = Candado(tmp_path / "a.lock")
    assert c1.tomar() is True
    c2 = Candado(tmp_path / "a.lock")
    assert c2.tomar() is False
    c1.liberar()
    assert c2.tomar() is True
    c2.liberar()


def test_segundo_proceso_sale_ocupado_sin_trabajar(tmp_path):
    ruta = tmp_path / "tenis-sportsapipro.lock"
    marca = tmp_path / "trabajo.txt"
    tenedor = _tenedor(ruta)
    try:
        assert intentar(ruta, lambda: marca.write_text("hecho")) == OCUPADO
        assert not marca.exists()
    finally:
        tenedor.kill()
        tenedor.wait()


def test_el_candado_se_libera_cuando_el_primero_muere(tmp_path):
    ruta = tmp_path / "tenis-sportsapipro.lock"
    tenedor = _tenedor(ruta)
    assert intentar(ruta, lambda: "x") == OCUPADO
    tenedor.kill()
    tenedor.wait()
    # El sistema operativo libera el bloqueo de un proceso muerto; en Windows puede tardar unos milisegundos tras
    # `wait()` (falló 2 de 6 ejecuciones al comprobarlo al instante). Se espera hasta 3 s: la liberación debe ocurrir.
    import time
    limite = time.monotonic() + 3.0
    resultado = intentar(ruta, lambda: "trabajo")
    while resultado == OCUPADO and time.monotonic() < limite:
        time.sleep(0.05)
        resultado = intentar(ruta, lambda: "trabajo")
    assert resultado == "trabajo"


def test_con_bloque_with_lanza_si_esta_ocupado(tmp_path):
    ruta = tmp_path / "tenis-sportsapipro.lock"
    tenedor = _tenedor(ruta)
    try:
        try:
            with Candado(ruta):
                raise AssertionError("no debería entrar")
        except RuntimeError as exc:
            assert str(exc) == OCUPADO
    finally:
        tenedor.kill()
        tenedor.wait()
