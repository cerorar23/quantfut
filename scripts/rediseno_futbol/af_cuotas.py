"""
Respaldo de cuotas de API-Football (tabla retirada el 1-nov-2026; 23-sep → 24-oct, 10 casas, 723 partidos de 23 ligas) con
el mismo método de `cuotas_reales.py`: la opción más probable de cada partido con cuota real ≥ 1,28 y si el porcentaje de
la casa se cumple. Sin motor propio: solo mide al mercado (Pinnacle y, donde no cotiza, la mediana de las demás casas) en
la escalera completa de líneas.

    python scripts/rediseno_futbol/af_cuotas.py --raiz .local/betsapi_futbol --datos .local/rediseno_20261101b

Necesita `af_odds.csv.gz` (conversión del respaldo COPY). «T-60» = último precio con ≥ 60 minutos de antelación; «último» =
último precio disponible (el respaldo no llega más cerca del saque que 28 minutos, así que no es el cierre).
Se une con `opciones_t60.csv.gz` de PropLine (23-oct → 1-nov) para el resultado conjunto. Solo lectura de archivos locales.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from qf.eval.rediseno_acierto import calibracion_alta, seleccion_diaria, wilson

CUOTA_MIN = 1.40  # decisión del titular (2-nov-2026); --cuota-min la cambia
MERCADOS = ["h2h", "double_chance", "spreads", "totals", "btts", "team_totals_home", "team_totals_away", "corners",
            "corners_home", "corners_away", "cards"]


def cargar_cuotas_reales():
    ruta = Path(__file__).resolve().parent / "cuotas_reales.py"
    spec = importlib.util.spec_from_file_location("cuotas_reales", ruta)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def construir_opciones(filas: pd.DataFrame, partidos: pd.DataFrame, cr, minimo: int) -> pd.DataFrame:
    """
    Opciones de cada partido con la mejor cuota entre casas, su resultado y la probabilidad sin margen de la casa
    (Pinnacle y, donde no cotiza, la mediana de las demás). `filas`: match_id, bookmaker, market, selection, line, price,
    mins_to_kickoff; se toma, por opción y casa, el último precio con al menos `minimo` minutos de antelación.
    """
    reales = partidos.set_index("match_id")
    af = filas
    s = af[af["mins_to_kickoff"] >= minimo].sort_values("mins_to_kickoff")
    s = s.groupby(["match_id", "bookmaker", "market", "selection", "line"], dropna=False, as_index=False).head(1)
    sm = cr.sin_margen(s)
    pin = sm[sm["casa"].eq("pinnacle")].set_index(["match_id", "mercado", "seleccion", "linea"])["q"]
    resto = sm[~sm["casa"].eq("pinnacle")].groupby(["match_id", "mercado", "seleccion", "linea"])["q"].median()
    s = s.assign(linea=s["line"].fillna(-999))
    o = s.groupby(["match_id", "market", "selection", "linea"], as_index=False).agg(cuota=("price", "max"))
    res, pn, ot = [], [], []
    for mid, mk, sel, ln, cu in o.itertuples(index=False):
        res.append(cr.resultado(mk, sel, ln, reales.loc[mid]))
        k = (mid, mk, sel, ln)
        pn.append(pin.get(k, np.nan)); ot.append(resto.get(k, np.nan))
    o = o.rename(columns={"market": "mercado", "selection": "seleccion"}).assign(resultado=res, pinnacle=pn, otras_casas=ot)
    o["mercado_p"] = o["pinnacle"].fillna(o["otras_casas"])
    o = o[o["resultado"].isin(["gana", "pierde"])]
    o["acierto"] = (o["resultado"] == "gana").astype(float)
    o = o.merge(partidos[["match_id", "kickoff_utc"]], on="match_id")
    return o


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", default=".local/betsapi_futbol")
    ap.add_argument("--cuota-min", type=float, default=1.40, help="cuota mínima de las opciones publicables")
    ap.add_argument("--datos", default=".local/rediseno_20261101b")
    a = ap.parse_args()
    global CUOTA_MIN
    CUOTA_MIN = a.cuota_min
    raiz, d = Path(a.raiz), Path(a.datos)
    cr = cargar_cuotas_reales()
    partidos = pd.read_csv(d / "partidos.csv.gz", parse_dates=["kickoff_utc"])
    reales = partidos.set_index("match_id")
    af = pd.read_csv(raiz / "af_odds.csv.gz", low_memory=False)
    af = af[af["market"].isin(MERCADOS) & af["match_id"].isin(reales.index) & af["price"].gt(1)]
    af = af[af["line"].isna() | ((af["line"] * 2) % 1 == 0)]  # sin líneas de cuarto
    af = af.rename(columns={"price": "price"})
    print(f"respaldo: {len(af)} filas de {af['match_id'].nunique()} partidos de las ligas del núcleo; "
          f"{af['bookmaker'].nunique()} casas")
    salida = []
    for nombre, minimo in (("T-60", 60), ("último", 0)):
        o = construir_opciones(af, partidos, cr, minimo)
        o["dia"] = o["kickoff_utc"].dt.strftime("%Y-%m-%d")
        o["fuente_cuotas"] = "api_football"
        o.to_csv(raiz / f"af_opciones_{nombre.replace('-', '').replace('ú', 'u')}.csv.gz", index=False)
        salida.append((nombre, o))
        informe(f"API-Football, {nombre}", o)
    pl = pd.read_csv(raiz.parent / "rediseno_20261101b" / "opciones_t60.csv.gz")
    t60 = salida[0][1]
    comun = ["match_id", "mercado", "seleccion", "linea", "cuota", "pinnacle", "otras_casas", "mercado_p", "acierto", "dia"]
    junto = pd.concat([t60[comun], pl[comun]], ignore_index=True)
    informe("API-Football T-60 + PropLine T-60 (23-sep → 1-nov)", junto)


def informe(titulo: str, o: pd.DataFrame) -> None:
    x = o[(o["cuota"] >= CUOTA_MIN) & o["mercado_p"].notna()]
    print(f"\n######## {titulo}: {o['match_id'].nunique()} partidos, {len(o)} opciones; con cuota ≥ {CUOTA_MIN} y probabilidad de casa: {len(x)} "
          f"(Pinnacle {x['pinnacle'].notna().mean():.0%})")
    filas = []
    for fuente in ("mercado_p", "pinnacle", "otras_casas"):
        y = x[x[fuente].notna()]
        m = y.sort_values(fuente, ascending=False).drop_duplicates("match_id")
        s = seleccion_diaria(m.assign(prob=m[fuente]), coberturas=(0.1, 0.3, 1.0)).set_index("cobertura")
        lo, hi = wilson(m["acierto"].sum(), len(m))
        filas.append({"fuente": fuente, "partidos": len(m), "acierto": m["acierto"].mean(), "ic95": f"[{lo:.3f};{hi:.3f}]",
                      "anuncia": m[fuente].mean(), "cuota": m["cuota"].mean(), "top10_acierto": s.loc[0.1, "acierto"],
                      "top10_anuncia": s.loc[0.1, "anunciado"], "top10_n": int(s.loc[0.1, "n"]),
                      "top30_acierto": s.loc[0.3, "acierto"], "top30_anuncia": s.loc[0.3, "anunciado"]})
    print(pd.DataFrame(filas).round(3).to_string(index=False))
    m = x.sort_values("mercado_p", ascending=False).drop_duplicates("match_id")
    print("   Mercado elegido como mejor opción:", m["mercado"].value_counts().head(6).to_dict())
    print("   Calibración de todas las opciones con cuota ≥ 1,28 (mercado_p):")
    print(calibracion_alta(x["mercado_p"].to_numpy(), x["acierto"].to_numpy(), cortes=(0.5, 0.6, 0.7, 0.8, 1.0001)).round(3).to_string(index=False))
    print("   Por mercado (mejor opción de cada partido):")
    tab = []
    for mk, g in x.groupby("mercado"):
        mm = g.sort_values("mercado_p", ascending=False).drop_duplicates("match_id")
        tab.append({"mercado": mk, "partidos": len(mm), "acierto": mm["acierto"].mean(), "anuncia": mm["mercado_p"].mean(), "cuota": mm["cuota"].mean()})
    print(pd.DataFrame(tab).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
