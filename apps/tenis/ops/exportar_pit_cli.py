# apps/tenis/ops/exportar_pit_cli.py
"""Exportación punto en el tiempo del histórico de tenis (solo lectura de la base) y, opcionalmente, la prueba de
equivalencia con la puerta oficial `*_a_las` sobre una muestra aleatoria.

Uso: python exportar_pit_cli.py [--esquema tenis_dev] [--salida DIR] [--desde 2005-01-01] [--verificar 300]
         [--semilla 20261105] [--hilos 4]
"""
import argparse
import json
import os
import sys
import time
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from tenis.datos import equivalencia, exportar_pit  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exportación PIT de tenis (Parquet + manifiesto)")
    ap.add_argument("--esquema", default="tenis_dev")
    ap.add_argument("--salida", type=Path, default=exportar_pit.SALIDA_POR_OMISION)
    ap.add_argument("--desde", type=date.fromisoformat, default=None)
    ap.add_argument("--verificar", type=int, default=0, help="partidos al azar para la prueba de equivalencia")
    ap.add_argument("--semilla", type=int, default=20261105)
    ap.add_argument("--hilos", type=int, default=4)
    ap.add_argument("--solo-verificar", action="store_true", help="no exporta; verifica la exportación existente")
    a = ap.parse_args(argv)
    dsn = os.environ.get("PG_DSN") or os.environ.get("QF_TEST_PG_DSN")
    t0 = time.time()
    if not a.solo_verificar:
        man = exportar_pit.exportar(dsn, a.esquema, a.salida, a.desde)
        print(json.dumps({"sha256_export": man["sha256_export"], "recuentos": man["recuentos"],
                          "ficheros": man["ficheros"], "segundos": round(time.time() - t0, 1)}, indent=1), flush=True)
    if a.verificar:
        t1 = time.time()
        res = equivalencia.verificar(dsn, a.esquema, a.salida, a.verificar, a.semilla, a.hilos)
        res["segundos"] = round(time.time() - t1, 1)
        (a.salida / "equivalencia_puerta.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
        print(json.dumps(res, indent=1, default=str), flush=True)
        return 0 if res["identico"] else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
