"""Aplica db/*.sql a una base vacía para las pruebas con Postgres real (GitHub Actions y local).

Las migraciones que siembran datos a partir de historia ya cargada (024, 033, 049-051...) no se pueden
aplicar sobre una base vacía: se listan y se sigue, porque las pruebas solo necesitan el esquema.
Uso: PGBASE=postgresql://usuario:clave@host:puerto python scripts/ci_aplicar_esquema.py
Con SIN_EXTENSIONES=1 se omiten pgcrypto y citext (un Postgres embebido sin contrib las pierde).
"""
import glob
import os
import re
import sys

import psycopg

base = os.environ["PGBASE"].rstrip("/")
sin_ext = os.getenv("SIN_EXTENSIONES") == "1"
with psycopg.connect(base + "/postgres", autocommit=True) as c:
    c.execute("DROP DATABASE IF EXISTS qf_test")
    c.execute("CREATE DATABASE qf_test")
fallos = []
with psycopg.connect(base + "/qf_test", autocommit=True) as c:
    for ruta in sorted(glob.glob("db/*.sql")):
        sql = open(ruta, encoding="utf-8").read()
        if sin_ext:
            sql = re.sub(r"CREATE EXTENSION IF NOT EXISTS (pgcrypto|citext);", "", sql)
            sql = re.sub(r"\bCITEXT\b", "TEXT", sql, flags=re.I)
        try:
            c.execute(sql)
        except Exception as exc:  # noqa: BLE001
            fallos.append((os.path.basename(ruta), str(exc).splitlines()[0][:140]))
            try:
                c.execute("ROLLBACK")
            except Exception:  # noqa: BLE001
                pass
print(f"migraciones: {len(glob.glob('db/*.sql'))}, no aplicables sobre una base vacía: {len(fallos)}")
for f in fallos:
    print("  ", f)
sys.exit(0)
