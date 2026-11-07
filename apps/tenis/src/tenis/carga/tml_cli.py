"""CLI de la carga TML (evidencia retro).

  python -m tenis.carga.tml_cli --snapshot <dir>/tml/originals --dsn <dsn> --esquema tenis

El manifiesto (`download_manifest.json`) está dos niveles por encima de `originals`. Cada fichero se verifica por
tamaño y sha256 antes de cargarse; si no coincide, se rechaza entero y se registra.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import time
from collections import Counter
from pathlib import Path

import psycopg

from . import tml_escritor as w
from .tml_carga import Fichero, Rechazos, cargar, filas

PATRON_CARGA = re.compile(r"^(\d{4})(_wta|_challenger)?\.csv$")
PATRON_QUALI = re.compile(r"^atp_quali/\d{4}_atp_quali\.csv$")
NO_CARGADOS = {
    "ATP_Database.csv": "base agregada que repite los ficheros anuales",
    "atp_matches_amateur.csv": "partidos amateur, fuera del alcance",
}
ESQUEMA = re.compile(r"^[a-z_][a-z0-9_]*$")
EQUIVALENCIAS = Path(__file__).resolve().parents[3] / "config" / "equivalencias.csv"


def _orden(nombre: str) -> tuple:
    anio = int(re.search(r"(\d{4})", nombre).group(1))
    grupo = 3 if "quali" in nombre else 1 if "_wta" in nombre else 2 if "challenger" in nombre else 0
    return grupo, anio, nombre


def listar(snapshot: Path) -> tuple[list[str], list[tuple[str, str, int]]]:
    """(ficheros a cargar, [(nombre, motivo, filas) no cargados])."""
    cargar_, no = [], []
    for p in snapshot.rglob("*.csv"):
        nombre = p.relative_to(snapshot).as_posix()
        if PATRON_CARGA.match(nombre) or PATRON_QUALI.match(nombre):
            cargar_.append(nombre)
            continue
        if "ongoing" in nombre:
            motivo = "partidos en curso, duplicados y sin resultado"
        else:
            motivo = NO_CARGADOS.get(nombre, "no reconocido")
        no.append((nombre, motivo, sum(1 for _ in filas(p.read_bytes()))))
    return sorted(cargar_, key=_orden), sorted(no)


def ficheros_verificados(snapshot: Path, nombres: list[str], manifiesto: dict) -> list[Fichero]:
    por_nombre = {f["name"]: f for f in manifiesto["files"] if f.get("source") == "tml"}
    salida = []
    for nombre in nombres:
        raw = (snapshot / nombre).read_bytes()
        e = por_nombre.get(nombre)
        motivo = None
        if e is None:
            motivo = "fichero_fuera_del_manifiesto"
        elif len(raw) != e["bytes"] or hashlib.sha256(raw).hexdigest() != e["sha256"]:
            motivo = "fichero_sha_no_coincide"
        salida.append(Fichero(nombre, raw, e, motivo))
    return salida


def cargar_equivalencias(ruta: Path) -> dict:
    """Equivalencias manuales de TML: id_alias → id_principal. Fichero ausente = sin equivalencias."""
    if not ruta.exists():
        return {}
    with open(ruta, encoding="utf-8", newline="") as f:
        return {r["id_alias"]: r["id_principal"] for r in csv.DictReader(f) if r["fuente"] == "tml"}


def _conteos(cur) -> dict:
    return {t: w.contar(cur, t) for t in ("recibo", "jugador", "jugador_alias", "jugador_asercion", "torneo",
                                           "edicion", "partido", "resultado", "estadistica", "ranking")}


def ejecutar(snapshot: Path, dsn: str, esquema: str, manifiesto: Path, almacen: Path, rechazos: Path,
             equivalencias: Path = EQUIVALENCIAS) -> dict:
    if not ESQUEMA.match(esquema):
        raise ValueError("nombre de esquema no válido")
    t0 = time.time()
    man = json.loads(manifiesto.read_text(encoding="utf-8"))
    lote = "tml_" + man["snapshot_created_at"][:10].replace("-", "")
    nombres, no_cargados = listar(snapshot)
    ficheros = ficheros_verificados(snapshot, nombres, man)
    log = Rechazos(rechazos)
    with psycopg.connect(dsn, autocommit=False) as conn:
        cur = conn.cursor()
        cur.execute(f"SET search_path TO {esquema}, public")
        antes = _conteos(cur)
        conn.commit()
        cont: Counter = cargar(conn, ficheros, almacen, lote, log, cargar_equivalencias(equivalencias))
        despues = _conteos(cur)
        conn.commit()
    log.cerrar()
    leidas = cont["leidas"]
    buckets = cont["cargado"] + cont["duplicado"] + cont["doble"] + sum(
        v for k, v in cont.items() if k.startswith("rechazo:"))
    return {"lote": lote, "ficheros_cargados": len(nombres), "ficheros_rechazados": sum(f.motivo is not None
                                                                                      for f in ficheros),
            "no_cargados": no_cargados, "leidas": leidas, "cuadra": leidas == buckets, "contadores": cont,
            "antes": antes, "despues": despues, "segundos": round(time.time() - t0, 1)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Carga de TML (retro) en la evidencia de tenis")
    ap.add_argument("--snapshot", required=True, type=Path, help="carpeta tml/originals")
    ap.add_argument("--dsn", default=os.environ.get("PG_DSN"))
    ap.add_argument("--esquema", default="tenis")
    ap.add_argument("--almacen", type=Path)
    ap.add_argument("--manifiesto", type=Path)
    ap.add_argument("--rechazos", type=Path)
    args = ap.parse_args(argv)
    snap = args.snapshot.resolve()
    raiz = snap.parents[1]
    nombre = raiz.name
    res = ejecutar(snap, args.dsn, args.esquema, args.manifiesto or raiz / "download_manifest.json",
                   args.almacen or raiz / "almacen_objetos", args.rechazos or raiz / f"rechazos_tml_{nombre}.csv")
    for k, v in res.items():
        if k not in ("contadores",):
            print(f"{k}: {v}")
    for k in sorted(res["contadores"]):
        print(f"  {k}: {res['contadores'][k]}")
    return 0 if res["cuadra"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
