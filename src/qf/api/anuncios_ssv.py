"""Verificación de callbacks SSV de AdMob (anuncios con recompensa).

Google firma con ECDSA P-256 + SHA-256 (firma DER en base64 url-safe sin relleno) el texto de
la consulta anterior a `&signature=`. `signature` y `key_id` van siempre al final y en ese
orden. Las claves públicas rotan: se cachean como máximo 24 h.
https://developers.google.com/admob/flutter/ssv
"""
from __future__ import annotations

import base64
import json
import time
import urllib.request

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

KEYS_URL = 'https://www.gstatic.com/admob/reward/verifier-keys.json'
MAX_AGE = 24 * 3600
RELOAD_UNKNOWN = 60

_clock = time.monotonic
_cache: dict = {'keys': {}, 'at': None, 'tried': None}


class SignatureError(Exception):
    """El callback no es auténtico o no tiene la forma que firma Google."""


class KeysUnavailable(Exception):
    """No se pudieron obtener las claves públicas; Google reintenta si respondemos 5xx."""


def split_signed(raw_query: str) -> tuple[str, str, str]:
    marker = '&signature='
    if raw_query.count(marker) != 1 or raw_query.count('&key_id=') != 1:
        raise SignatureError('estructura')
    content, rest = raw_query.split(marker, 1)
    signature, sep, key_id = rest.partition('&key_id=')
    if not content or not sep or not signature or not key_id or '&' in signature or '&' in key_id:
        raise SignatureError('estructura')
    return content, signature, key_id


def parse_keys(payload: dict) -> dict[str, bytes]:
    return {str(k['keyId']): base64.b64decode(k['base64']) for k in payload['keys']}


def verify(raw_query: str, keys: dict[str, bytes]) -> None:
    content, signature, key_id = split_signed(raw_query)
    der = keys.get(key_id)
    if der is None:
        raise SignatureError('key_id desconocido')
    try:
        raw = base64.urlsafe_b64decode(signature + '=' * (-len(signature) % 4))
        key = serialization.load_der_public_key(der)
        key.verify(raw, content.encode('ascii'), ec.ECDSA(hashes.SHA256()))
    except (InvalidSignature, ValueError, TypeError) as e:
        raise SignatureError('firma') from e


def _fetch() -> dict:
    with urllib.request.urlopen(KEYS_URL, timeout=5) as r:  # noqa: S310 - URL fija de Google
        return json.loads(r.read())


def reset_cache() -> None:
    _cache.update(keys={}, at=None, tried=None)


def keys_for(key_id: str, fetch=None) -> dict[str, bytes]:
    fetch = fetch or _fetch
    now = _clock()
    empty = not _cache['keys']
    stale = _cache['at'] is None or now - _cache['at'] > MAX_AGE
    unknown = key_id not in _cache['keys'] and (_cache['tried'] is None or now - _cache['tried'] > RELOAD_UNKNOWN)
    if empty or stale or unknown:
        _cache['tried'] = now
        try:
            _cache['keys'] = parse_keys(fetch())
            _cache['at'] = now
        except Exception as e:  # noqa: BLE001 - red, JSON o formato
            if empty or stale:
                raise KeysUnavailable(str(e)) from e
    return _cache['keys']
