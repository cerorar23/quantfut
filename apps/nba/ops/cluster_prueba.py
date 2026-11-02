"""Clúster Postgres temporal para las pruebas de NBA; nunca toca la base de fútbol.

    python apps/nba/ops/cluster_prueba.py start   # imprime el DSN administrador
    python apps/nba/ops/cluster_prueba.py stop

Usa los binarios de NBA_PG_BIN (por defecto la instalación de Postgres 16 de Windows)
y escucha solo en 127.0.0.1:55432 con autenticación `trust`.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

PUERTO = 55432
DATOS = Path(tempfile.gettempdir()) / "nba_pg_prueba"
BIN = Path(os.environ.get("NBA_PG_BIN", r"C:\Program Files\PostgreSQL\16\bin"))
DSN = f"postgresql://postgres@127.0.0.1:{PUERTO}/postgres"


def _ejecutar(exe, *args):
    # El servidor hereda la salida: sin redirigirla, pg_ctl deja colgado al proceso que lo lanzó.
    subprocess.run([str(BIN / exe), *args], check=True, stdout=subprocess.DEVNULL)


def start():
    if not (DATOS / "PG_VERSION").exists():
        _ejecutar("initdb", "-D", str(DATOS), "-U", "postgres", "-A", "trust", "-E", "UTF8")
    _ejecutar("pg_ctl", "-D", str(DATOS), "-l", str(DATOS / "log.txt"), "-w",
              "-o", f'-p {PUERTO} -c listen_addresses=127.0.0.1', "start")
    print(DSN)


def stop():
    _ejecutar("pg_ctl", "-D", str(DATOS), "-m", "fast", "-w", "stop")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("start", "stop"):
        sys.exit(__doc__)
    {"start": start, "stop": stop}[sys.argv[1]]()
