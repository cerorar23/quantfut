"""CLI de la carga SofaScore (tenis, retro).

  python -m tenis.carga.sofascore_cli --indice <csv> --raiz <SOFASCORE/data/v3> --dsn <dsn> --esquema tenis \
      --almacen <carpeta> --rechazos <csv>

El índice es el de `apps/tennis/ops/inventario_sofascore.py` (una fila por partido). No modifica el archivo de origen.
"""
import argparse
import os
import re
import time
from collections import Counter
from pathlib import Path

import psycopg

from .sofascore_carga import cargar, leer_gz_desde, leer_indice

ESQUEMA = re.compile(r"^[a-z_][a-z0-9_]*$")


def ejecutar(indice: Path, raiz: Path, dsn: str, esquema: str, almacen: Path, rechazos: Path | None,
             entradas=None, fabrica_resolutor=None) -> dict:
    """Carga el índice (o `entradas` ya filtradas) en `esquema`. Devuelve contadores, tiempos y el cuadre."""
    if not ESQUEMA.match(esquema):
        raise ValueError("nombre de esquema no válido")
    t0 = time.time()
    lista = entradas if entradas is not None else leer_indice(indice)
    with psycopg.connect(dsn, autocommit=False) as conn:
        cur = conn.cursor()
        cur.execute(f"SET search_path TO {esquema}, public")
        conn.commit()
        cont: Counter = cargar(conn, lista, leer_gz_desde(raiz), almacen, rechazos, fabrica_resolutor=fabrica_resolutor)
    categorias = sum(v for k, v in cont.items() if k.startswith(("rechazo:", "excluido:", "duplicado:")))
    cuadra = cont["leidas"] == cont["cargado"] + cont["ya_cargado"] + categorias
    return {"leidas": cont["leidas"], "cuadra": cuadra, "contadores": cont,
            "segundos": round(time.time() - t0, 1)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Carga de SofaScore (tenis, retro) en la evidencia")
    ap.add_argument("--indice", required=True, type=Path)
    ap.add_argument("--raiz", required=True, type=Path, help="carpeta data/v3 de SofaScore")
    ap.add_argument("--dsn", default=os.environ.get("PG_DSN"))
    ap.add_argument("--esquema", default="tenis")
    ap.add_argument("--almacen", required=True, type=Path)
    ap.add_argument("--rechazos", type=Path)
    args = ap.parse_args(argv)
    res = ejecutar(args.indice, args.raiz, args.dsn, args.esquema, args.almacen, args.rechazos)
    print(f"leidas: {res['leidas']}  cuadra: {res['cuadra']}  segundos: {res['segundos']}")
    for k in sorted(res["contadores"]):
        print(f"  {k}: {res['contadores'][k]}")
    return 0 if res["cuadra"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
