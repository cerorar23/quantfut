"""Conciliación de la carga SofaScore con la auditoría (solo esquema aislado; sin crear bases ni roles).

  python -m ops.conciliar_sofascore  (desde apps/tenis/, con PYTHONPATH=src)  o  python apps/tenis/ops/conciliar_sofascore.py

Crea un esquema `tenis_c_<hex>` (y su `_op`), aplica las migraciones de evidencia, carga el archivo completo, compara los
recuentos con las cifras de la auditoría, y borra el esquema al terminar (también si falla).
"""
import argparse
import csv
import json
import os
import re
import sys
import time
import uuid
from collections import Counter
from pathlib import Path

import psycopg
from psycopg import sql

RAIZ_APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_APP / "src"))

from tenis.carga.sofascore_cli import ejecutar  # noqa: E402

DB = RAIZ_APP / "db"
MIGRACIONES = ["0001_catalogos.sql", "0002_evidencia.sql", "0003_inmutabilidad.sql", "0004_lectura_pit.sql",
               "0006_sellado.sql", "0007_semillas.sql"]
_PATRON = re.compile(r"\btenis(_op)?(?=[.;,\s)]|$)")
AUDITORIA = {"filas": 21974, "finished": 21913, "canceled": 61, "atp": 11186, "wta": 10788,
             "bo3": 19881, "bo5": 2032, "pbp_o_estadistica": 20816, "ronda_vacia": 459, "ronda_vacia_alt": 458,
             "desde": "2022-12-30", "hasta": "2026-11-03"}


def sql_de(nombre: str, esquema: str, esquema_op: str) -> str:
    texto = (DB / nombre).read_text(encoding="utf-8")
    return _PATRON.sub(lambda m: esquema_op if m.group(1) else esquema, texto)


def indice_resumen(ruta: Path) -> dict:
    """Recuentos del índice (auditoría) para contrastar con lo que se carga."""
    c: Counter = Counter()
    fechas = []
    with open(ruta, encoding="utf-8", newline="") as f:
        for fila in csv.DictReader(f):
            c["filas"] += 1
            c[fila["estado"]] += 1
            c[fila["circuito_categoria"]] += 1
            c[f"bo{fila['mejor_de']}"] += 1
            if not fila["ronda"]:
                c["ronda_vacia"] += 1
            if fila["ficheros_evento"] and ("point_by_point.json.gz" in fila["ficheros_evento"]
                                            or "statistics.json.gz" in fila["ficheros_evento"]):
                c["pbp_o_estadistica"] += 1
            if fila["fecha_utc"]:
                fechas.append(fila["fecha_utc"][:10])
            if fila["dobles"] == "True":
                c["dobles"] += 1
    return {"contadores": dict(c), "desde": min(fechas) if fechas else None,
            "hasta": max(fechas) if fechas else None}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--indice", required=True, type=Path)
    ap.add_argument("--raiz", required=True, type=Path)
    ap.add_argument("--almacen", required=True, type=Path)
    ap.add_argument("--rechazos", required=True, type=Path)
    ap.add_argument("--salida", type=Path, help="JSON con los resultados")
    args = ap.parse_args(argv)
    dsn = os.environ["PG_DSN"]
    sufijo = uuid.uuid4().hex[:10]
    esquema, esquema_op = f"tenis_c_{sufijo}", f"tenis_c_{sufijo}_op"
    resultado = {}
    with psycopg.connect(dsn, autocommit=True) as db:
        db.execute(f"CREATE SCHEMA {esquema}")
        db.execute(f"CREATE SCHEMA {esquema_op}")
        try:
            for m in MIGRACIONES:
                db.execute(sql_de(m, esquema, esquema_op))
            t0 = time.time()
            carga = ejecutar(args.indice, args.raiz, dsn, esquema, args.almacen, args.rechazos)
            resultado["carga"] = {k: v for k, v in carga.items() if k != "contadores"}
            resultado["contadores"] = carga["contadores"]
            resultado["segundos_carga"] = round(time.time() - t0, 1)
            with db.cursor() as cur:
                cur.execute(f"SET search_path TO {esquema}")
                resultado["base"] = {
                    "partido": cur.execute("SELECT count(*) FROM partido").fetchone()[0],
                    "estado": dict(cur.execute("SELECT estado, count(*) FROM resultado GROUP BY 1").fetchall()),
                    "mejor_de": dict(cur.execute("SELECT mejor_de, count(*) FROM partido GROUP BY 1").fetchall()),
                    "circuito": dict(cur.execute("SELECT t.circuito, count(*) FROM partido p JOIN edicion e "
                                                 "ON e.edicion_id = p.edicion_id JOIN torneo t ON t.torneo_id = "
                                                 "e.torneo_id GROUP BY 1").fetchall()),
                    "juego_pbp_partidos": cur.execute("SELECT count(DISTINCT partido_id) FROM juego_pbp").fetchone()[0],
                    "estadistica_partidos": cur.execute("SELECT count(DISTINCT partido_id) FROM estadistica").fetchone()[0],
                    "jugadores": cur.execute("SELECT count(*) FROM jugador").fetchone()[0],
                    "torneos": cur.execute("SELECT count(*) FROM torneo").fetchone()[0],
                    "ediciones": cur.execute("SELECT count(*) FROM edicion").fetchone()[0],
                    "recibos": cur.execute("SELECT count(*) FROM recibo").fetchone()[0],
                }
        finally:
            db.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(esquema)))
            db.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(esquema_op)))
    resultado["indice"] = indice_resumen(args.indice)
    resultado["auditoria"] = AUDITORIA
    if args.salida:
        args.salida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(resultado, ensure_ascii=False, indent=2, default=str))
    return 0 if resultado["carga"]["cuadra"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
