"""Cifrado en reposo de secretos (secret keys de proveedores de ofertas).

AES-256-GCM (AEAD) de `cryptography`: confidencialidad + integridad. Cada valor
usa un nonce aleatorio de 96 bits y se liga a un `contexto` (AAD) para que un
secreto cifrado de un proveedor no se pueda copiar a la fila de otro.

La clave maestra vive SOLO en el entorno del servidor (QF_SECRETS_KEY), nunca
en la base de datos: quien copie la BD no puede descifrar nada. Rotación:
poner la clave nueva en QF_SECRETS_KEY y la anterior en QF_SECRETS_KEY_OLD;
se descifra con cualquiera y `reencrypt()` guarda con la nueva.

Genera una clave con:  python -m qf.comercial.cifrado
"""
from __future__ import annotations

import base64
import binascii
import os
import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

VERSION = 'v1'
ENV_KEY = 'QF_SECRETS_KEY'
ENV_OLD = 'QF_SECRETS_KEY_OLD'


class CifradoError(Exception):
    """Falta la clave, la clave es inválida o el dato está alterado."""


def generar_clave() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()


def _clave(valor: str) -> bytes:
    try:
        raw = base64.urlsafe_b64decode(valor.strip().encode())
    except (binascii.Error, ValueError):
        raise CifradoError('Clave maestra con formato inválido') from None
    if len(raw) != 32:
        raise CifradoError('La clave maestra debe tener 32 bytes (AES-256)')
    return raw


def _claves() -> list[bytes]:
    nueva = os.getenv(ENV_KEY, '')
    if not nueva:
        raise CifradoError(f'Falta {ENV_KEY} en el servidor')
    return [_clave(v) for v in (nueva, os.getenv(ENV_OLD, '')) if v]


def disponible() -> bool:
    try:
        _claves()
        return True
    except CifradoError:
        return False


def cifrar(texto: str, contexto: str) -> str:
    nonce = secrets.token_bytes(12)
    ct = AESGCM(_claves()[0]).encrypt(nonce, texto.encode(), f'{VERSION}:{contexto}'.encode())
    return f'{VERSION}:' + base64.urlsafe_b64encode(nonce + ct).decode()


def descifrar(token: str, contexto: str) -> str:
    version, _, cuerpo = token.partition(':')
    if version != VERSION or not cuerpo:
        raise CifradoError('Formato de secreto no reconocido')
    try:
        blob = base64.urlsafe_b64decode(cuerpo.encode())
    except (binascii.Error, ValueError):
        raise CifradoError('Secreto corrupto') from None
    if len(blob) < 12 + 16:
        raise CifradoError('Secreto corrupto')
    nonce, ct = blob[:12], blob[12:]
    for clave in _claves():
        try:
            return AESGCM(clave).decrypt(nonce, ct, f'{VERSION}:{contexto}'.encode()).decode()
        except InvalidTag:
            continue
    raise CifradoError('No se pudo descifrar: clave incorrecta o dato alterado')


if __name__ == '__main__':
    print(generar_clave())
