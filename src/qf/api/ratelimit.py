"""Rate limiting por ventana fija sobre Redis. `INCR` es atómico: dos
peticiones concurrentes en el mismo segundo no pueden pisarse el contador."""
from __future__ import annotations

import ipaddress
import time

from fastapi import Request


def rate_limited(redis_client, key: str, limit: int, window_seconds: int = 60) -> bool:
    """True si `key` YA superó `limit` peticiones en la ventana actual."""
    bucket = f"ratelimit:{key}:{int(time.time()) // window_seconds}"
    count = redis_client.incr(bucket)
    if count == 1:
        redis_client.expire(bucket, window_seconds)
    return count > limit


def client_ip(request: Request) -> str:
    # Detrás de Caddy en la misma red de Compose: confiar en X-Forwarded-For
    # es correcto porque el proxy lo escribe él, el cliente no puede falsearlo
    # sin pasar por Caddy primero.
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "desconocida")


def client_key(request: Request) -> str:
    """IP del cliente; en IPv6, su /64. Un cliente IPv6 suele controlar un /64
    entero, y rotar direcciones dentro de él anulaba el límite por IP."""
    ip = client_ip(request)
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return ip
    if addr.version == 4:
        return str(addr)
    if addr.ipv4_mapped:
        return str(addr.ipv4_mapped)
    return str(ipaddress.ip_network(f"{ip}/64", strict=False))
