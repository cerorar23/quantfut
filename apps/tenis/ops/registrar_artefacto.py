"""Registra o reactiva un artefacto del motor de tenis (plan §H.1, §H.4). Por omisión solo VALIDA y muestra el plan (sin tocar la base).

  python apps/tenis/ops/registrar_artefacto.py validar --json apps/tenis/artefactos/tenis-2.1-capa-edad.json \
         --informe <evaluacion_wf_capa_edad.json> [--menor 1]
  python apps/tenis/ops/registrar_artefacto.py registrar --json ... --informe ... --imagen tenis-motor:<tag> \
         --aprobado-en-chat "<texto del OK del titular>" [--dsn <dsn> | PG_DSN] [--esquema tenis] --ejecutar
  python apps/tenis/ops/registrar_artefacto.py reactivar --sha256 <sha del artefacto anterior> --imagen tenis-motor:<tag> \
         --aprobado-en-chat "<OK>" --ejecutar          # vuelta atrás

`registrar` y `reactivar` sin `--ejecutar` solo imprimen lo que harían. Con `--ejecutar` exigen el OK escrito del titular.
El DSN debe ser de un rol que pueda INSERTAR en artefacto y artefacto_activo (el motor solo lee). Nunca se imprime el DSN.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

import psycopg

from tenis import artefactos as art


def _conectar(a):
    if not a.dsn:
        sys.exit("falta --dsn o PG_DSN")
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", a.esquema):
        sys.exit("nombre de esquema no válido")
    db = psycopg.connect(a.dsn, autocommit=True)
    db.execute(f"SET search_path TO {a.esquema}, public")
    return db


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("accion", choices=["validar", "registrar", "reactivar"])
    ap.add_argument("--json", type=Path)
    ap.add_argument("--informe", type=Path)
    ap.add_argument("--menor", type=int, default=1)
    ap.add_argument("--sha256")
    ap.add_argument("--imagen")
    ap.add_argument("--aprobado-en-chat", default="")
    ap.add_argument("--dsn", default=os.environ.get("PG_DSN"))
    ap.add_argument("--esquema", default="tenis")
    ap.add_argument("--ejecutar", action="store_true")
    a = ap.parse_args(argv)

    if a.accion in ("validar", "registrar"):
        if not a.json or not a.informe:
            sys.exit("--json e --informe son obligatorios")
        plan = art.validar(a.json, a.informe, a.menor)
        print(json.dumps({k: plan[k] for k in ("sha256", "version_modelo", "capa_edad", "advertencias")}, indent=1, ensure_ascii=False))
        if a.accion == "validar":
            return 0
        print(f"imagen: {a.imagen}\naprobado_en_chat: {a.aprobado_en_chat!r}")
        if not a.ejecutar:
            print("(sin --ejecutar: no se ha tocado la base)")
            return 0
        with _conectar(a) as db:
            print(json.dumps(art.registrar(db, plan, a.imagen, a.aprobado_en_chat), indent=1, default=str, ensure_ascii=False))
        return 0

    if not a.sha256:
        sys.exit("--sha256 es obligatorio")
    if not a.ejecutar:
        print(f"reactivaría {a.sha256} con la imagen {a.imagen} (sin --ejecutar: no se ha tocado la base)")
        return 0
    with _conectar(a) as db:
        print(json.dumps(art.reactivar(db, a.sha256, a.imagen, a.aprobado_en_chat), indent=1, default=str, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
