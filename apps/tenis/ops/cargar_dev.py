# apps/tenis/ops/cargar_dev.py
"""Carga TML y SofaScore en un esquema LOCAL PERSISTENTE de desarrollo (por omisión `tenis_dev`) para entrenar y evaluar.

NO es la base de producción: es un esquema aparte de la base local de desarrollo (se borra con
`DROP SCHEMA tenis_dev, tenis_dev_op CASCADE`). El orden es el obligatorio: TML primero y SofaScore después, con el
resolutor multifuente (une los jugadores de las dos fuentes). Si el esquema ya existe, se REUTILIZA sin tocarlo
(las cargas son idempotentes: repetirlas no añade filas).

Uso: python cargar_dev.py <tml/originals> [--esquema tenis_dev]
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import psycopg
from psycopg import sql

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "tests"))
from db_util import MIGRACIONES, sql_de  # noqa: E402
from tenis.carga import sofascore_cli, tml_cli  # noqa: E402
from tenis.identidad import enlazar  # noqa: E402
from tenis.identidad.resolver import ResolutorMultifuente, cargar_equivalencias  # noqa: E402

INDICE = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\rediseno_20261104\tablas\sofascore_local_tenis_eventos.csv")
RAIZ_SOFA = Path(r"C:\Users\huye\Documents\SOFASCORE\data\v3")
ALMACEN = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\rediseno_20261104\almacen_dev")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("snapshot", type=Path)
    ap.add_argument("--esquema", default="tenis_dev")
    a = ap.parse_args()
    dsn = os.environ.get("PG_DSN") or os.environ.get("QF_TEST_PG_DSN")
    esquema = a.esquema
    snap = a.snapshot.resolve()
    raiz = snap.parents[1]
    ALMACEN.mkdir(parents=True, exist_ok=True)
    with psycopg.connect(dsn, autocommit=True) as admin:
        existe = admin.execute("SELECT 1 FROM information_schema.schemata WHERE schema_name = %s", (esquema,)).fetchone()
        if not existe:
            for m in MIGRACIONES:
                admin.execute(sql_de(m, esquema, esquema + "_op"))
    t = time.time()
    r = tml_cli.ejecutar(snap, dsn, esquema, raiz / "download_manifest.json", ALMACEN / "tml", ALMACEN / "rechazos_tml.csv")
    print("TML:", r["leidas"], "cuadra", r["cuadra"], r["despues"], round(time.time() - t), "s", flush=True)
    nombres, _ = tml_cli.listar(snap)
    with psycopg.connect(dsn, autocommit=True) as db:
        db.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(esquema)))
        edades = enlazar.edades_para_resolutor(db.cursor(), list(enlazar.filas_tml([snap / n for n in nombres])))
    equiv = cargar_equivalencias(RAIZ / "config" / "equivalencias.csv")
    t = time.time()
    s = sofascore_cli.ejecutar(INDICE, RAIZ_SOFA, dsn, esquema, ALMACEN / "sofa", ALMACEN / "rechazos_sofa.csv",
                               fabrica_resolutor=lambda conn: ResolutorMultifuente(conn, equivalencias=equiv, edades=edades))
    print("SofaScore:", s["leidas"], "cuadra", s["cuadra"], round(time.time() - t), "s", flush=True)
    with psycopg.connect(dsn, autocommit=True) as db:
        db.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(esquema)))
        filas = {t_: db.execute(f"SELECT count(*) FROM {t_}").fetchone()[0]
                 for t_ in ("jugador", "partido", "resultado", "estadistica", "juego_pbp", "programa", "ranking", "edicion")}
    print(json.dumps({"esquema": esquema, "filas": filas}, indent=1))


if __name__ == "__main__":
    main()
