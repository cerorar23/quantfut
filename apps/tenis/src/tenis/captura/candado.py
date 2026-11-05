"""Candado exclusivo, no bloqueante, por fuente. Multiplataforma: `fcntl.flock` en Linux, `msvcrt.locking` en Windows.

Si el candado ya está tomado por otro proceso, `intentar` devuelve OCUPADO sin ejecutar el trabajo. El sistema
operativo libera el candado cuando el proceso muere, así que un proceso caído no deja el candado tomado.
"""
import os
import sys
from pathlib import Path
from typing import Callable, TypeVar

T = TypeVar("T")
OCUPADO = "ocupado"


class Candado:
    def __init__(self, ruta) -> None:
        self.ruta = Path(ruta)
        self._fd: int | None = None

    def tomar(self) -> bool:
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.ruta, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            if sys.platform == "win32":
                import msvcrt

                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            return False
        self._fd = fd
        return True

    def liberar(self) -> None:
        if self._fd is None:
            return
        fd, self._fd = self._fd, None
        try:
            if sys.platform == "win32":
                import msvcrt

                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def __enter__(self) -> "Candado":
        if not self.tomar():
            raise RuntimeError(OCUPADO)
        return self

    def __exit__(self, *_exc) -> None:
        self.liberar()


def intentar(ruta, trabajo: Callable[[], T]) -> T | str:
    """Ejecuta `trabajo` si se obtiene el candado; si no, devuelve la cadena «ocupado» sin hacer nada."""
    candado = Candado(ruta)
    if not candado.tomar():
        return OCUPADO
    try:
        return trabajo()
    finally:
        candado.liberar()
