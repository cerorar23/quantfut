"""
Medición semanal (solo lectura del servidor): ¿el porcentaje que anuncia la casa se cumple con las cuotas reales de PropLine?

    python scripts/rediseno_futbol/remedir_semana.py [--desde 2026-10-23] [--cuota-min 1.40]

Exporta con `exportar_semana.sql` los partidos terminados con cuotas de PropLine y sus precios a T-60 y al cierre; arma las
opciones como en `af_cuotas.construir_opciones` (mejor cuota entre casas; probabilidad = Pinnacle sin margen y, donde no
cotiza, la mediana de las demás casas) y, con cuota ≥ `--cuota-min`, mide la mejor opción de cada partido. Imprime la
muestra acumulada y los últimos 7 días, y guarda las opciones en `.local/remedir/AAAAMMDD_{t60,cierre}.csv.gz`.
Meta: ≥ 500 partidos con cuota a T-60 (hoy ≈ 150) para estrechar el intervalo (±8 puntos con 128 partidos).
"""
from __future__ import annotations

import argparse
import importlib.util
import io
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from qf.eval.rediseno_acierto import calibracion_alta, wilson

AQUI = Path(__file__).resolve().parent


def cargar(nombre: str):
    spec = importlib.util.spec_from_file_location(nombre, AQUI / f"{nombre}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def exportar(desde: str) -> dict[str, pd.DataFrame]:
    sql = (AQUI / "exportar_semana.sql").read_bytes()
    r = subprocess.run(["ssh", "quantfut", f"docker exec -i quantfut-db-1 psql -U qf -d quantfut -X -v ON_ERROR_STOP=1 -v desde={desde}"],
                       input=sql, capture_output=True, check=True)
    bloques, actual, buf = {}, None, []
    for linea in r.stdout.decode("utf-8").splitlines():
        if linea.startswith("@@ "):
            if actual:
                bloques[actual] = "\n".join(buf)
            actual, buf = linea[3:].strip(), []
        elif actual:
            buf.append(linea)
    return {k: pd.read_csv(io.StringIO(v), low_memory=False) for k, v in bloques.items() if k != "fin" and v.strip()}


def resumen(titulo: str, o: pd.DataFrame, cuota_min: float) -> None:
    x = o[(o["cuota"] >= cuota_min) & o["mercado_p"].notna()]
    m = x.sort_values("mercado_p", ascending=False).drop_duplicates("match_id")
    if m.empty:
        print(f"{titulo}: sin opciones"); return
    lo, hi = wilson(m["acierto"].sum(), len(m))
    print(f"{titulo}: {len(m)} partidos; mejor opción con cuota ≥ {cuota_min}: acierto {m['acierto'].mean():.3f} [{lo:.3f};{hi:.3f}], "
          f"anuncia {m['mercado_p'].mean():.3f}, cuota media {m['cuota'].mean():.2f}; Pinnacle en {m['pinnacle'].notna().mean():.0%}")
    cal = calibracion_alta(x["mercado_p"].to_numpy(), x["acierto"].to_numpy(), cortes=(0.5, 0.6, 0.7, 0.8, 1.0001))
    print(cal.round(3).to_string(index=False))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", default="2026-10-23")
    ap.add_argument("--cuota-min", type=float, default=1.40)
    ap.add_argument("--salida", default=".local/remedir")
    a = ap.parse_args()
    af = cargar("af_cuotas")
    cr = af.cargar_cuotas_reales()
    bloques = exportar(a.desde)
    partidos = bloques["partidos"]
    partidos["kickoff_utc"] = pd.to_datetime(partidos["kickoff_utc"], utc=True)
    print(f"{len(partidos)} partidos terminados con PropLine desde {a.desde}")
    Path(a.salida).mkdir(parents=True, exist_ok=True)
    corte7 = partidos["kickoff_utc"].max() - pd.Timedelta(days=7)
    for nombre, clave in (("T-60", "cuotas_t60"), ("cierre", "cuotas_cierre")):
        filas = bloques[clave]
        filas = filas[filas["market"].isin(af.MERCADOS) & filas["match_id"].isin(partidos["match_id"]) & filas["price"].gt(1)]
        filas = filas[filas["line"].isna() | ((filas["line"] * 2) % 1 == 0)]
        o = af.construir_opciones(filas, partidos, cr, 0)
        o["dia"] = o["kickoff_utc"].dt.strftime("%Y-%m-%d")
        o.to_csv(Path(a.salida) / f"{date.today():%Y%m%d}_{nombre.replace('-', '').lower()}.csv.gz", index=False)
        print(f"\n===== {nombre} =====")
        resumen("acumulado", o, a.cuota_min)
        resumen("últimos 7 días", o[o["kickoff_utc"] > corte7], a.cuota_min)


if __name__ == "__main__":
    main()
