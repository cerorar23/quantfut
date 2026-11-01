"""Registro de cada pasada de ingesta en `ingest_health` (lo lee `health.py` y el panel)."""
from __future__ import annotations

import json


def record_health(source: str, rows: int, ok: bool, detail: dict | None = None) -> None:
    from ..db import execute
    execute(
        """INSERT INTO ingest_health (source, rows_written, ok, detail)
           VALUES (%s, %s, %s, %s)""",
        (source, rows, ok, json.dumps(detail or {})),
    )
