"""Rate limiting por ventana fija sobre Redis. `INCR` es atómico: dos
peticiones concurrentes en el mismo segundo no pueden pisarse el contador."""
from __future__ import annotations

import time


def rate_limited(redis_client, key: str, limit: int, window_seconds: int = 60) -> bool:
    """True si `key` YA superó `limit` peticiones en la ventana actual."""
    bucket = f"ratelimit:{key}:{int(time.time()) // window_seconds}"
    count = redis_client.incr(bucket)
    if count == 1:
        redis_client.expire(bucket, window_seconds)
    return count > limit
