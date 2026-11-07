# apps/tenis/ops/medir_identidad.py
"""Identidad de jugadores: medir el enlace entre fuentes, o proponer equivalencias de TML.

  # Mide sobre un esquema ya cargado (TML + la otra fuente). Solo lectura. Requiere PG_DSN.
  python apps/tenis/ops/medir_identidad.py --esquema tenis --fuente sofascore --auditoria <ruta.csv>

  # Propone equivalencias de ids de TML (solo CSV de salida; no toca la base) y compara con el puente antiguo.
  python apps/tenis/ops/medir_identidad.py --propuestas-tml <tml/originals> --salida <ruta.csv> \
      [--puente <identity_report.json>]
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]           # apps/tenis
sys.path.insert(0, str(RAIZ / "src"))

from tenis.carga.tml_cli import _orden, listar  # noqa: E402
from tenis.identidad import enlazar, propuestas  # noqa: E402

ESQUEMA = re.compile(r"^[a-z_][a-z0-9_]*$")


def _medir(args) -> int:
    import psycopg
    if not ESQUEMA.match(args.esquema):
        raise SystemExit("nombre de esquema no válido")
    with psycopg.connect(os.environ["PG_DSN"], autocommit=True) as conn:
        cur = conn.cursor()
        cur.execute(f"SET search_path TO {args.esquema}, public")
        res = enlazar.medir(cur, fuente=args.fuente, referencia=args.referencia)
        n = enlazar.csv_auditoria(cur, Path(args.auditoria), args.fuente, args.referencia) if args.auditoria else None
    res["auditoria_filas"] = n
    print(json.dumps(res, indent=2, ensure_ascii=False, default=str))
    return 0


def _puente(res: dict, ruta: Path) -> None:
    """Compara cada fusión del puente antiguo con lo que propone esta medición (ids de TML)."""
    dato = json.loads(ruta.read_text(encoding="utf-8"))
    propuesto = {(p["circ"], p["id_alias"]): p["id_principal"] for p in res["propuestas"]}
    dudosa = {(d[0], d[3]): d[4] for d in res["dudosas"]}
    distinto = {(d["circ"], d["id"]) for d in res["distintos"]}
    print("\nPuente antiguo (fusiones por fecha de nacimiento):")
    for m in dato["merged"]:
        circ, alias = m["circuit"].lower(), m["id"].split(":", 1)[1]
        principal = m["base"].split(":", 1)[1]
        if propuesto.get((circ, alias)) == principal:
            veredicto = "propuesta igual"
        elif (circ, alias) in propuesto:
            veredicto = f"propuesta invertida (principal {propuesto[(circ, alias)]})"
        elif (circ, alias) in dudosa or (circ, principal) in dudosa:
            veredicto = f"dudosa: {dudosa.get((circ, alias), dudosa.get((circ, principal)))}"
        elif (circ, alias) in distinto:
            veredicto = "distinto por edad"
        else:
            veredicto = "sin evidencia de edad o de país (no propuesta)"
        print(f"  {m['circuit']} {alias} -> {principal} ({m['name']}): {veredicto}")
    print(f"  confirmados distintos en el puente: {len(dato['confirmed_distinct'])}")


def _propuestas(args) -> int:
    snap = Path(args.propuestas_tml)
    nombres, _ = listar(snap)
    res = propuestas.proponer(enlazar.filas_tml([snap / n for n in nombres]), _orden)
    propuestas.escribir_csv(res["propuestas"], Path(args.salida))
    print(f"propuestas: {len(res['propuestas'])}  dudosas: {len(res['dudosas'])}  distintos: {len(res['distintos'])}")
    motivos = {}
    for d in res["dudosas"]:
        clave = d[4].split("(")[0].split("_")[0]
        motivos[clave] = motivos.get(clave, 0) + 1
    print(f"motivos de dudosas: {motivos}")
    if args.puente:
        _puente(res, Path(args.puente))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Identidad de jugadores entre fuentes (medición y propuestas TML)")
    ap.add_argument("--esquema", default="tenis")
    ap.add_argument("--fuente", default="sofascore")
    ap.add_argument("--referencia", default="tml")
    ap.add_argument("--auditoria", help="CSV de auditoría por id de la fuente")
    ap.add_argument("--propuestas-tml", help="carpeta tml/originals")
    ap.add_argument("--salida", help="CSV de equivalencias propuestas")
    ap.add_argument("--puente", help="identity_report.json del puente antiguo")
    args = ap.parse_args(argv)
    if args.propuestas_tml:
        if not args.salida:
            raise SystemExit("--propuestas-tml requiere --salida")
        return _propuestas(args)
    return _medir(args)


if __name__ == "__main__":
    raise SystemExit(main())
