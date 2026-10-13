"""Ningún módulo de src/qf puede usar un nombre sin definir.

Regresión (2026-10-12): `mobile.py` usaba `Request` sin importarlo. Python no avisa al arrancar
(las anotaciones son cadenas con `from __future__ import annotations`) y FastAPI lo degradaba en
silencio a un parámetro de consulta, rompiendo el acceso con Google.
"""
from pathlib import Path

import pytest

pyflakes_api = pytest.importorskip("pyflakes.api")
pyflakes_reporter = pytest.importorskip("pyflakes.reporter")


class _Recolector:
    def __init__(self):
        self.avisos = []

    def unexpectedError(self, filename, msg):
        self.avisos.append(f"{filename}: {msg}")

    def syntaxError(self, filename, msg, lineno, offset, text):
        self.avisos.append(f"{filename}:{lineno}: {msg}")

    def flake(self, mensaje):
        if "undefined name" in str(mensaje.message % mensaje.message_args):
            self.avisos.append(str(mensaje))


def test_no_hay_nombres_indefinidos_en_src():
    raiz = Path(__file__).resolve().parents[1] / "src" / "qf"
    reporte = _Recolector()
    for archivo in sorted(raiz.rglob("*.py")):
        pyflakes_api.check(archivo.read_text(encoding="utf-8"), str(archivo), reporte)
    assert not reporte.avisos, "\n".join(reporte.avisos)
