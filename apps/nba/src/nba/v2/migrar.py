"""Ejecutor de migraciones de la base aislada `nba_*` (rediseño NBA, esquema `nba`)."""
import hashlib
import os
from pathlib import Path
import sys

import psycopg
from psycopg.conninfo import conninfo_to_dict

DIRECTORIO = Path(__file__).resolve().parents[3] / "db"
CANDADO = 74754155  # distinto del de nba_delivery (74754154)


def principal() -> int:
    """`NBA_DB_DSN=... python -m nba.v2.migrar`: aplica las migraciones pendientes e imprime sus versiones."""
    dsn = os.environ.get("NBA_DB_DSN")
    if not dsn:
        print("falta NBA_DB_DSN", file=sys.stderr)
        return 2
    for version in aplicar(dsn):
        print(version)
    return 0


def conectar(dsn: str) -> psycopg.Connection:
    if not conninfo_to_dict(dsn).get("dbname", "").startswith("nba_"):
        raise ValueError("se requiere una base aislada nba_* (nunca la de fútbol)")
    return psycopg.connect(dsn, connect_timeout=5)


def aplicar(dsn: str, directorio: Path | None = None) -> list[str]:
    archivos = sorted((directorio or DIRECTORIO).glob("*.sql"))
    aplicadas: list[str] = []
    with conectar(dsn) as db:
        with db.transaction():
            db.execute("SELECT pg_advisory_xact_lock(%s)", (CANDADO,))
            db.execute("CREATE SCHEMA IF NOT EXISTS nba")
            db.execute("CREATE TABLE IF NOT EXISTS nba.migracion (version TEXT PRIMARY KEY, "
                       "sha256 TEXT NOT NULL, aplicada_en TIMESTAMPTZ NOT NULL DEFAULT now())")
        for archivo in archivos:
            contenido = archivo.read_bytes().replace(b"\r\n", b"\n")  # la huella no depende del checkout (CRLF/LF)
            huella = hashlib.sha256(contenido).hexdigest()
            with db.transaction():
                db.execute("SELECT pg_advisory_xact_lock(%s)", (CANDADO,))
                previa = db.execute("SELECT sha256 FROM nba.migracion WHERE version = %s", (archivo.stem,)).fetchone()
                if previa:
                    if previa[0] != huella:
                        raise RuntimeError(f"la migración {archivo.stem} ya aplicada cambió de contenido")
                    continue
                db.execute(contenido.decode("utf-8"))
                db.execute("INSERT INTO nba.migracion (version, sha256) VALUES (%s, %s)", (archivo.stem, huella))
                aplicadas.append(archivo.stem)
    return aplicadas


if __name__ == "__main__":
    raise SystemExit(principal())
