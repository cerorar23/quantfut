"""Recibo de un original: qué se recibió, de dónde, cuándo, y dónde está el contenido.

Un recibo no guarda claves ni secretos: los parámetros con nombre sospechoso se rechazan antes de escribir nada.
"""
from datetime import datetime

from pydantic import Field

from .almacen import guardar_objeto, leer_objeto
from .contratos.base import Contrato, Hash256, Instante

__all__ = ["Recibo", "nuevo_recibo", "guardar_objeto", "leer_objeto"]

_NOMBRES_PROHIBIDOS = ("key", "token", "secret", "password", "auth")
Valor = str | int | float | bool | None


class Recibo(Contrato):
    fuente: str = Field(min_length=1)
    recurso: str = Field(min_length=1)
    parametros: dict[str, Valor]
    recibido_en: Instante
    estado_http: int | None = Field(default=None, ge=100, le=599)
    sha256: Hash256
    ruta_objeto: str
    bytes: int = Field(ge=0)
    retro: bool


def _sin_secretos(parametros: dict[str, Valor]) -> None:
    for nombre in parametros:
        if any(p in nombre.lower() for p in _NOMBRES_PROHIBIDOS):
            raise ValueError(f"parámetro «{nombre}» parece un secreto: no se guarda en el recibo")


def nuevo_recibo(
    raiz,
    *,
    fuente: str,
    recurso: str,
    parametros: dict[str, Valor],
    recibido_en: datetime,
    cuerpo: bytes,
    retro: bool,
    estado_http: int | None = None,
    extension: str = ".json.gz",
) -> Recibo:
    _sin_secretos(parametros)
    sha, ruta, _creado = guardar_objeto(raiz, cuerpo, extension)
    return Recibo(
        fuente=fuente,
        recurso=recurso,
        parametros=parametros,
        recibido_en=recibido_en,
        estado_http=estado_http,
        sha256=sha,
        ruta_objeto=ruta,
        bytes=len(cuerpo),
        retro=retro,
    )
