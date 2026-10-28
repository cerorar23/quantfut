"""Player portraits from fixed public CDN endpoints, cached outside the code image."""
import os
from pathlib import Path
import re
import struct
import tempfile
import threading
import time

import httpx

SOURCES = {
    "futbol": "https://media.api-sports.io/football/players/{}.png",
    "nba": "https://cdn.nba.com/headshots/nba/latest/260x190/{}.png",
}
MAX_BYTES = 512_000
_slots = threading.BoundedSemaphore(4)
_missing = {}
_lock = threading.Lock()


def photo_url(sport, player_id):
    value = str(player_id)
    if sport not in SOURCES or not re.fullmatch(r"[1-9][0-9]{0,7}", value):
        return None
    return f"/web/imagenes/jugadores/{sport}/{value}.png"


def valid_png(body):
    if len(body) < 33 or len(body) > MAX_BYTES or not body.startswith(b"\x89PNG\r\n\x1a\n"):
        return False
    if body[12:16] != b"IHDR":
        return False
    width, height = struct.unpack(">II", body[16:24])
    return 0 < width <= 2048 and 0 < height <= 2048 and body[-8:-4] == b"IEND"


def cached_portrait(sport, player_id, directory):
    """Only fixed providers and numeric IDs; no caller-supplied URLs or redirects."""
    if photo_url(sport, player_id) is None:
        return None
    target = Path(directory) / sport / f"{player_id}.png"
    if target.is_file() and valid_png(target.read_bytes()):
        return target
    key = sport, str(player_id)
    with _lock:
        if _missing.get(key, 0) > time.monotonic():
            return None
    if not _slots.acquire(timeout=12):
        return None
    temporary = None
    try:
        with httpx.Client(timeout=httpx.Timeout(8, connect=3), follow_redirects=False) as client:
            with client.stream("GET", SOURCES[sport].format(player_id), headers={"User-Agent": "QuantFutImages/1.0"}) as response:
                response.raise_for_status()
                if response.headers.get("content-type", "").split(";")[0] != "image/png":
                    raise ValueError("Not a PNG")
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise ValueError("Image too large")
                    chunks.append(chunk)
        body = b"".join(chunks)
        if not valid_png(body):
            raise ValueError("Invalid PNG")
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(body)
        os.replace(temporary, target)
        with _lock:
            _missing.pop(key, None)
        return target
    except (httpx.HTTPError, OSError, ValueError):
        with _lock:
            if len(_missing) >= 4096:
                _missing.clear()
            _missing[key] = time.monotonic() + 300
        return None
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)
        _slots.release()
