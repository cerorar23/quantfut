"""Acceso a Postgres. psycopg3, pool simple, sin ORM."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterable

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import settings

log = logging.getLogger(__name__)

_pool: ConnectionPool | None = None


def pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(settings.pg_dsn, min_size=1, max_size=6, open=True)
    return _pool


@contextmanager
def conn():
    with pool().connection() as c:
        c.row_factory = dict_row
        yield c


def query(sql: str, params: Iterable[Any] = ()) -> list[dict]:
    with conn() as c:
        with c.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def query_one(sql: str, params: Iterable[Any] = ()) -> dict | None:
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: Iterable[Any] = ()) -> int:
    with conn() as c:
        with c.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount


def executemany(sql: str, rows: list[tuple]) -> int:
    if not rows:
        return 0
    with conn() as c:
        with c.cursor() as cur:
            cur.executemany(sql, rows)
            return cur.rowcount


def copy_rows(table: str, columns: list[str], rows: list[tuple]) -> int:
    """Inserción masiva vía COPY. Mucho más rápido para snapshots de cuotas."""
    if not rows:
        return 0
    cols = ", ".join(columns)
    with conn() as c:
        with c.cursor() as cur:
            with cur.copy(f"COPY {table} ({cols}) FROM STDIN") as cp:
                for r in rows:
                    cp.write_row(r)
    return len(rows)
