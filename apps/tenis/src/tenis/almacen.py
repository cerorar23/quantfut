"""Almacén de originales direccionado por contenido: objetos/aa/<sha256>.json.gz.

Escritura atómica: el contenido comprimido va a un temporal en el mismo directorio, se fuerza a disco (fsync) y solo
entonces se publica con os.link, que falla si el destino ya existe. Un proceso interrumpido no deja nada en la ruta
definitiva; como mucho queda un temporal «.*.tmp» huérfano.
"""
import gzip
import hashlib
import os
import tempfile
import zlib
from pathlib import Path


def _ruta(sha: str) -> str:
    return f"objetos/{sha[:2]}/{sha}.json.gz"


def _verificar(destino: Path, sha: str) -> None:
    datos = destino.read_bytes()  # si falta, FileNotFoundError: no es corrupción
    try:
        cuerpo = gzip.decompress(datos)
    except (OSError, EOFError, zlib.error):
        raise ValueError("objeto corrupto") from None
    if hashlib.sha256(cuerpo).hexdigest() != sha:
        raise ValueError("objeto corrupto")


def guardar_objeto(raiz, cuerpo: bytes) -> tuple[str, str, bool]:
    """Devuelve (sha256, ruta_relativa, creado). creado=False si el mismo contenido ya estaba."""
    sha = hashlib.sha256(cuerpo).hexdigest()
    relativa = _ruta(sha)
    destino = Path(raiz) / relativa
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        _verificar(destino, sha)
        return sha, relativa, False
    descriptor, temporal = tempfile.mkstemp(dir=destino.parent, prefix=".", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "wb") as f:
            f.write(gzip.compress(cuerpo, mtime=0))
            f.flush()
            os.fsync(f.fileno())
        try:
            os.link(temporal, destino)
        except FileExistsError:
            _verificar(destino, sha)
            return sha, relativa, False
    finally:
        Path(temporal).unlink(missing_ok=True)
    return sha, relativa, True


def leer_objeto(raiz, sha: str) -> bytes:
    destino = Path(raiz) / _ruta(sha)
    _verificar(destino, sha)
    return gzip.decompress(destino.read_bytes())
