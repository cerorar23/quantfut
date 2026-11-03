"""
Acierto del pronóstico con cuota mínima 1,28 usando las cuotas REALES de PropLine (desde el 23-oct-2026), a T-60 y al
cierre, en vez del tope aproximado de probabilidad de `mercados.py`.

    PYTHONPATH=src python scripts/rediseno_futbol/cuotas_reales.py --datos .local/rediseno_20261101b --pred .local/rediseno_20261101

Una opción es cada (partido, mercado, selección, línea) con precio en alguna casa; se queda la mejor cuota entre
casas. Fuentes de probabilidad:
- `motor`: A0 con xG (1X2, doble, hándicap, totales, ambos marcan, goles por equipo), Yip (córners) y Dawson
  (tarjetas = amarillas + rojas a tasa de liga);
- `pinnacle`: Pinnacle sin margen en ese mismo mercado y línea (Shin en 1X2, proporcional en dos vías; la doble
  oportunidad sale de su 1X2);
- `otras_casas`: mediana de la probabilidad sin margen de las demás casas que cotizan ese mercado y línea;
- `mercado_p` (= `produccion`): Pinnacle y, donde no cotiza, las demás casas.
Las líneas de cuarto (x,25 / x,75) se dejan fuera. Por partido se toma la opción más probable con cuota ≥ 1,28 y
cada día se publica el top de partidos. Liga MX fuera (no está en los modelos).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import poisson

from qf.eval import rediseno as R
from qf.eval import rediseno_conteos as C
from qf.eval.rediseno_acierto import calibracion_alta, seleccion_diaria
from qf.eval.rediseno_mercados import liquidar, pmf_diferencia, pmf_suma, prob_linea
from qf.model.calibration import score_matrices
from qf.model.devig import devig

DESDE = "2026-10-23"
CUOTA_MIN = 1.40  # decisión del titular (2-nov-2026); --cuota-min la cambia
MERCADOS = ["h2h", "double_chance", "spreads", "totals", "btts", "team_totals_home", "team_totals_away", "corners",
            "corners_home", "corners_away", "cards"]


def probs_motor(mk, sel, linea, M, Pc, Ph, Pa, Pt):
    """(P gana, P devuelve) de una opción según el motor; None si no hay distribución."""
    if mk in ("h2h", "double_chance", "spreads", "totals", "btts", "team_totals_home", "team_totals_away"):
        if M is None:
            return None
        dif, sop = pmf_diferencia(M[None]); g = np.arange(M.shape[0])
        if mk == "h2h":
            k = {"home": sop > 0, "draw": sop == 0, "away": sop < 0}[sel]
            return dif[0, k].sum(), 0.0
        if mk == "double_chance":
            k = {"1X": sop >= 0, "X2": sop <= 0, "12": sop != 0}[sel]
            return dif[0, k].sum(), 0.0
        if mk == "spreads":  # la línea es el hándicap del equipo elegido
            d = dif if sel == "home" else dif[:, ::-1]
            a, b = prob_linea(d, sop, -linea, "mas")
            return a[0], b[0]
        if mk == "btts":
            p = M[1:, 1:].sum()
            return (p if sel == "yes" else 1 - p), 0.0
        pmf = (pmf_suma(M[None])[0] if mk == "totals" else M.sum(1) if mk.endswith("home") else M.sum(0))
        a, b = prob_linea(pmf[None], np.arange(len(pmf)), linea, "mas" if sel == "over" else "menos")
        return a[0], b[0]
    pmf = {"corners": Pc, "corners_home": Ph, "corners_away": Pa, "cards": Pt}[mk]
    if pmf is None or not np.isfinite(pmf).all():
        return None
    a, b = prob_linea(pmf[None], np.arange(len(pmf)), linea, "mas" if sel == "over" else "menos")
    return a[0], b[0]


def resultado(mk, sel, linea, r):
    hg, ag = r["home_goals"], r["away_goals"]
    if mk == "h2h":
        return "gana" if {"home": hg > ag, "draw": hg == ag, "away": hg < ag}[sel] else "pierde"
    if mk == "double_chance":
        return "gana" if {"1X": hg >= ag, "X2": hg <= ag, "12": hg != ag}[sel] else "pierde"
    if mk == "btts":
        return "gana" if ((hg > 0) & (ag > 0)) == (sel == "yes") else "pierde"
    if mk == "spreads":
        d = hg - ag if sel == "home" else ag - hg
        return str(liquidar(np.array([d]), -linea, "mas")[0])
    valor = {"totals": hg + ag, "team_totals_home": hg, "team_totals_away": ag,
             "corners": r["home_corners"] + r["away_corners"], "corners_home": r["home_corners"],
             "corners_away": r["away_corners"],
             "cards": r["home_yellow"] + r["away_yellow"] + r["home_red"] + r["away_red"]}[mk]
    if pd.isna(valor):
        return None
    return str(liquidar(np.array([float(valor)]), linea, "mas" if sel == "over" else "menos")[0])


def sin_margen(c: pd.DataFrame) -> pd.DataFrame:
    """
    Probabilidad sin margen de cada casa por opción: (partido, mercado, selección, línea, casa, q). Se normaliza
    dentro del mismo mercado y línea de la misma casa (Shin en 1X2, proporcional en dos vías). En el hándicap el
    local con línea L se empareja con el visitante con −L. La doble oportunidad se deduce del 1X2 de la casa
    (P(1X) = local + empate), que es más fiable que la doble que cotizan pocas casas.
    """
    p = c.copy()
    p["clave_linea"] = np.where(p["market"].eq("spreads"), np.where(p["selection"].eq("home"), p["line"], -p["line"]),
                                p["line"].fillna(-999))
    filas = []
    for (casa, mid, mk, cl), g in p.groupby(["bookmaker", "match_id", "market", "clave_linea"]):
        if mk == "double_chance":
            continue
        tam = 3 if mk == "h2h" else 2
        if len(g) != tam or g["selection"].nunique() != tam:
            continue
        q = devig(g["price"].to_numpy(), "shin") if mk == "h2h" else (1 / g["price"]) / (1 / g["price"]).sum()
        for (sel, ln), v in zip(g[["selection", "line"]].itertuples(index=False), np.asarray(q)):
            filas.append((mid, mk, sel, -999 if pd.isna(ln) else ln, casa, float(v)))
        if mk == "h2h":
            h = dict(zip(g["selection"], np.asarray(q)))
            for sel, v in (("1X", h["home"] + h["draw"]), ("X2", h["away"] + h["draw"]), ("12", h["home"] + h["away"])):
                filas.append((mid, "double_chance", sel, -999, casa, float(v)))
    return pd.DataFrame(filas, columns=["match_id", "mercado", "seleccion", "linea", "casa", "q"])


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", default=".local/rediseno_20261101b")
    ap.add_argument("--cuota-min", type=float, default=1.40, help="cuota mínima de las opciones publicables")
    ap.add_argument("--pred", default=".local/rediseno_20261101")
    a = ap.parse_args()
    global CUOTA_MIN
    CUOTA_MIN = a.cuota_min
    d, dp = Path(a.datos), Path(a.pred)
    datos = R.cargar(d)
    df = R.tabla_partidos(datos)
    partidos = pd.read_csv(d / "partidos.csv.gz", parse_dates=["kickoff_utc"])
    reales = partidos.set_index("match_id")
    rojas = partidos[partidos["kickoff_utc"] < pd.Timestamp("2024-07-01", tz="UTC")][["home_red", "away_red"]].sum(1).mean()

    recientes = df[df["kickoff_utc"] >= pd.Timestamp(DESDE, tz="UTC")]
    pred = pd.read_csv(dp / "pred_f3.csv.gz").query("modelo == 'a0_xg'").set_index("match_id")
    ruta = d / "pred_conteos_recientes.csv.gz"
    if ruta.exists():
        pc = pd.read_csv(ruta)
    else:  # el motor C con el 1X2 de PropLine (sin él, supremacía e igualdad quedan vacías desde el 23-oct)
        der = pd.read_csv(d / "derbis.csv.gz")
        Lc = C.rasgos(df, datos.contexto, der, datos.equipo, "corners")
        Ly = C.rasgos(df, datos.contexto, der, datos.equipo, "yellow")
        pc = pd.concat([C.walk_forward(Lc, "corners", ["c2_yip"], "2026-10-20", por_lado=True),
                        C.walk_forward(Ly, "yellow", ["t3_dawson"], "2026-10-20")], ignore_index=True)
        pc.to_csv(ruta, index=False)
    cor = pc[pc["variante"] == "c2_yip"].set_index("match_id")
    yel = pc[pc["variante"] == "t3_dawson"].set_index("match_id")
    print(f"partidos desde {DESDE}: {len(recientes)}; con A0 {recientes['match_id'].isin(pred.index).sum()}, "
          f"córners {recientes['match_id'].isin(cor.index).sum()}, amarillas {recientes['match_id'].isin(yel.index).sum()}; "
          f"rojas por partido {rojas:.3f}")

    dist = {}
    for mid in recientes["match_id"]:
        M = None
        if mid in pred.index:
            f = pred.loc[mid]
            M = score_matrices(np.array([f["lam"]]), np.array([f["mu"]]), float(f["rho"]))[0]
        Pc = cor.loc[mid].filter(regex=r"^p\d+$").to_numpy(float) if mid in cor.index else None
        Ph = cor.loc[mid].filter(regex=r"^h\d+$").to_numpy(float) if mid in cor.index else None
        Pa = cor.loc[mid].filter(regex=r"^a\d+$").to_numpy(float) if mid in cor.index else None
        Pt = None
        if mid in yel.index:  # tarjetas = amarillas (Dawson) + rojas (Poisson a la tasa de liga)
            py = yel.loc[mid].filter(regex=r"^p\d+$").to_numpy(float)
            Pt = np.convolve(py, poisson.pmf(np.arange(4), rojas))[:len(py)]
        dist[mid] = (M, Pc, Ph, Pa, Pt)

    for nombre, archivo in (("T-60", "cuotas_t60.csv.gz"), ("cierre", "cuotas.csv.gz")):
        c = pd.read_csv(d / archivo, low_memory=False)
        c = c[c["source"].eq("propline") & c["market"].isin(MERCADOS) & c["match_id"].isin(dist)]
        c = c[c["line"].isna() | ((c["line"] * 2) % 1 == 0)]  # sin líneas de cuarto
        sm = sin_margen(c)
        pin = sm[sm["casa"].eq("pinnacle")].set_index(["match_id", "mercado", "seleccion", "linea"])["q"]
        resto = sm[~sm["casa"].eq("pinnacle")].groupby(["match_id", "mercado", "seleccion", "linea"])["q"].median()
        por_casa = sm.pivot_table(index=["match_id", "mercado", "seleccion", "linea"], columns="casa", values="q")
        c["linea"] = c["line"].fillna(-999)
        o = c.groupby(["match_id", "market", "selection", "linea"]).agg(cuota=("price", "max")).reset_index()
        filas = []
        for mid, mk, sel, ln, cuota in o.itertuples(index=False):
            r = reales.loc[mid]
            res = resultado(mk, sel, ln, r)
            pm = probs_motor(mk, sel, ln, *dist[mid])
            k = (mid, mk, sel, ln)
            filas.append({"match_id": mid, "mercado": mk, "seleccion": sel, "linea": ln, "cuota": cuota, "resultado": res,
                          "motor": np.nan if pm is None else pm[0] / max(1 - pm[1], 1e-9),
                          "devuelve_motor": np.nan if pm is None else pm[1], "pinnacle": pin.get(k, np.nan),
                          "otras_casas": resto.get(k, np.nan)})
        o = pd.DataFrame(filas)
        o["mercado_p"] = o["pinnacle"].fillna(o["otras_casas"])  # Pinnacle y, donde no cotiza, la mediana de las demás
        o["produccion"] = o["mercado_p"]
        o = o.merge(por_casa.add_prefix("casa_").reset_index(), on=["match_id", "mercado", "seleccion", "linea"], how="left")
        o = o.merge(df[["match_id", "kickoff_utc"]], on="match_id")
        o["dia"] = o["kickoff_utc"].dt.strftime("%Y-%m-%d")
        o = o[o["resultado"].isin(["gana", "pierde"])]  # el acierto no cuenta devoluciones
        o["acierto"] = (o["resultado"] == "gana").astype(float)
        o.to_csv(d / f"opciones_{nombre.lower().replace('-', '')}.csv.gz", index=False)
        print(f"\n######## {nombre}: {o['match_id'].nunique()} partidos, {len(o)} opciones, "
              f"{(o['cuota'] >= CUOTA_MIN).mean():.1%} con cuota ≥ {CUOTA_MIN}")
        for fuente in ("mercado_p", "pinnacle", "otras_casas", "motor"):
            x = o[(o["cuota"] >= CUOTA_MIN) & o[fuente].notna()]
            mejor = x.sort_values(fuente, ascending=False).drop_duplicates("match_id")
            sel = seleccion_diaria(mejor.assign(prob=mejor[fuente]), coberturas=(0.1, 0.3, 0.5, 1.0))
            print(f"\n-- {fuente}: la opción más probable de cada partido con cuota ≥ {CUOTA_MIN}; cuota media "
                  f"{mejor['cuota'].mean():.2f}; mercados elegidos {mejor['mercado'].value_counts().head(5).to_dict()}")
            print(sel.round(3).to_string(index=False))
            top1 = mejor[mejor.groupby("dia")[fuente].rank(ascending=False, method="first") == 1]
            print(f"   1 por día: n {len(top1)}, acierto {top1['acierto'].mean():.3f}, anunciado {top1[fuente].mean():.3f}")
            print(f"   calibración de TODAS las opciones con cuota ≥ {CUOTA_MIN}:")
            print(calibracion_alta(x[fuente].to_numpy(), x["acierto"].to_numpy(), cortes=(0.5, 0.6, 0.7, 0.8, 1.0001))
                  .round(3).to_string(index=False))
        # honestidad de cada casa: todas las opciones que cotiza (cualquier cuota), tramo 0,6–0,8 y Brier
        print("\n   honestidad por casa (opciones 0,6–0,8 y Brier en las opciones comunes con Pinnacle):")
        for col in sorted(x for x in o.columns if x.startswith("casa_")):
            v = o[o[col].notna()]
            alta = v[v[col].between(0.6, 0.8)]
            com = v[v["casa_pinnacle"].notna()] if col != "casa_pinnacle" else v
            print(f"   {col[5:]:14s} opciones {len(v):5d}  0,6–0,8: n {len(alta):4d} anuncia {alta[col].mean():.3f} ocurre "
                  f"{alta['acierto'].mean():.3f}  Brier {((com[col] - com['acierto']) ** 2).mean():.4f} frente a Pinnacle "
                  f"{((com['casa_pinnacle'] - com['acierto']) ** 2).mean():.4f} (n {len(com)})")
        # ¿el tope aproximado (p ≤ 74,4 %) acierta con la cuota real?
        t = o[o["produccion"].notna()]
        tope = 1 / (CUOTA_MIN * 1.05)
        print(f"\n   tope aproximado p ≤ {tope:.3f}: de las opciones bajo el tope, {(t[t['produccion'] <= tope]['cuota'] >= CUOTA_MIN).mean():.1%} "
              f"tienen cuota real ≥ {CUOTA_MIN}; de las que lo superan, {(t[t['produccion'] > tope]['cuota'] >= CUOTA_MIN).mean():.1%}")


if __name__ == "__main__":
    main()
