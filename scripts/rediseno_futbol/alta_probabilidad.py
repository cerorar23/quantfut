"""
¿Qué fuente da el pronóstico con MAYOR probabilidad de acertar, y anuncia un porcentaje verdadero? (1-nov-2026)

Por familia (1X2, doble oportunidad, goles, córners, amarillas) cada fuente propone, por partido, su opción más
probable; cada día se publica el top 5/10/20/30/50/100 % y se mide el acierto y la promesa incumplida
(anunciado − acertado). Con cuotas (1X2 y doble oportunidad) se repite exigiendo cuota ≥ 1,40, la mínima del
destacado de la app. Periodo 24/25 → hoy, solo filas con mercado.

    PYTHONPATH=src python scripts/rediseno_futbol/alta_probabilidad.py [--datos ...]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from qf.eval import rediseno as R
from qf.eval.rediseno_acierto import calibracion_alta, seleccion_diaria
from qf.model.calibration import score_matrices
from qf.model.market_anchor import market_lambdas

EVAL = "2024-07-01"
CUOTA_MIN = 1.40
MARGEN = 0.04  # margen supuesto de la casa en goles, córners y tarjetas (no hay histórico de cuotas)


def tope() -> float:
    """Probabilidad máxima de una opción sin cuota histórica para que su cuota real llegue a CUOTA_MIN."""
    return 1 / (CUOTA_MIN * (1 + MARGEN))
DOBLE = {"1X": (0, 1), "X2": (1, 2), "12": (0, 2)}


def goles(lam, mu, rho) -> dict[str, np.ndarray]:
    m = score_matrices(np.asarray(lam, float), np.asarray(mu, float), float(rho))
    g = np.arange(m.shape[1]); tot = g[:, None] + g[None, :]
    out = {f"mas_{l}": m[:, tot > l].sum(1) for l in (1.5, 2.5, 3.5)}
    out["ambos"] = m[:, 1:, 1:].sum((1, 2))
    return out


def candidatos_resultado(base: pd.DataFrame, p: np.ndarray, odds: np.ndarray | None) -> dict[str, pd.DataFrame]:
    """Opción más probable por partido en 1X2 y en doble oportunidad (con su cuota real si hay)."""
    oc = base["outcome"].to_numpy()
    k = p.argmax(1)
    res = {"1x2": pd.DataFrame({"dia": base["dia"], "match_id": base["match_id"], "familia": "1x2", "prob": p.max(1), "acierto": (k == oc).astype(int),
                                "cuota": odds[np.arange(len(k)), k] if odds is not None else np.nan})}
    pd_ = np.stack([p[:, a] + p[:, b] for a, b in DOBLE.values()], 1)
    kd = pd_.argmax(1)
    pares = list(DOBLE.values())
    ac = np.array([oc[i] in pares[kd[i]] for i in range(len(kd))]).astype(int)
    cuota_d = (1 / (1 / odds[np.arange(len(kd)), [pares[j][0] for j in kd]]
                    + 1 / odds[np.arange(len(kd)), [pares[j][1] for j in kd]])) if odds is not None else np.nan
    res["doble"] = pd.DataFrame({"dia": base["dia"], "match_id": base["match_id"], "familia": "doble", "prob": pd_.max(1), "acierto": ac, "cuota": cuota_d})
    return res


def candidatos_goles(base: pd.DataFrame, lam, mu, rho) -> pd.DataFrame:
    gl = goles(lam, mu, rho)
    tot = (base["home_goals"] + base["away_goals"]).to_numpy()
    ambos = ((base["home_goals"] > 0) & (base["away_goals"] > 0)).to_numpy()
    opciones = []
    for l in (1.5, 2.5, 3.5):
        p = gl[f"mas_{l}"]
        opciones += [(p, tot > l), (1 - p, tot < l)]
    opciones += [(gl["ambos"], ambos), (1 - gl["ambos"], ~ambos)]
    P = np.stack([o[0] for o in opciones], 1); A = np.stack([o[1] for o in opciones], 1)
    # sin cuota en el histórico: se limita a opciones de probabilidad ≤ 1/1,40 para no publicar lo trivial
    P_lim = np.where(P <= tope(), P, -1)
    k = P_lim.argmax(1)
    return pd.DataFrame({"dia": base["dia"], "match_id": base["match_id"], "familia": "goles", "prob": P_lim[np.arange(len(k)), k],
                         "acierto": A[np.arange(len(k)), k].astype(int)})


def candidatos_conteo(datos_dir: Path, objetivo: str, lineas, base: pd.DataFrame) -> dict[str, pd.DataFrame]:
    pred = pd.read_csv(datos_dir / f"pred_f4_{objetivo}.csv.gz")
    col = f"home_{objetivo}"
    real = base.set_index("match_id")[[col, f"away_{objetivo}", "dia"]].dropna()
    out = {}
    for v, g in pred.groupby("variante"):
        g = g.set_index("match_id").loc[lambda x: x.index.intersection(real.index)]
        P = g.filter(like="p").to_numpy(); r = real.loc[g.index]
        tot = (r[col] + r[f"away_{objetivo}"]).to_numpy()
        ops_p, ops_a = [], []
        for l in lineas:
            mas = P[:, int(l) + 1:].sum(1)
            ops_p += [mas, 1 - mas]; ops_a += [tot > l, tot < l]
        Pm = np.stack(ops_p, 1); Am = np.stack(ops_a, 1)
        Pm = np.where(Pm <= tope(), Pm, -1)
        k = Pm.argmax(1)
        out[v] = pd.DataFrame({"dia": r["dia"].to_numpy(), "match_id": g.index.to_numpy(), "familia": objetivo,
                               "prob": Pm[np.arange(len(k)), k],
                               "acierto": Am[np.arange(len(k)), k].astype(int)})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", default=".local/rediseno_20261101")
    ap.add_argument("--cuota-min", type=float, default=1.40)
    ap.add_argument("--margen", type=float, default=0.04)
    a = ap.parse_args()
    global CUOTA_MIN, MARGEN
    CUOTA_MIN, MARGEN = a.cuota_min, a.margen
    d = Path(a.datos)
    df = R.tabla_partidos(R.cargar(d))
    df["dia"] = df["kickoff_utc"].dt.strftime("%Y-%m-%d")
    base = df[(df["kickoff_utc"] >= pd.Timestamp(EVAL, tz="UTC")) & df["mk_home"].notna()].reset_index(drop=True)
    pred = pd.read_csv(d / "pred_extras.csv.gz")
    odds = base[["odd_home", "odd_draw", "odd_away"]].to_numpy()

    fuentes = {"mercado": base[["mk_home", "mk_draw", "mk_away"]].to_numpy()}
    for m in ("a0_xg", "dc_prod", "logit_apilado", "gbm_apilado_mercado"):
        x = base[["match_id"]].merge(pred[pred["modelo"] == m], on="match_id", how="left")
        fuentes[m] = x[["p_home", "p_draw", "p_away"]].to_numpy()
    comunes = ~np.isnan(np.column_stack(list(fuentes.values()))).any(1)
    base, odds = base[comunes].reset_index(drop=True), odds[comunes]
    fuentes = {k: v[comunes] for k, v in fuentes.items()}

    familias: dict[str, dict[str, pd.DataFrame]] = {"1x2": {}, "doble": {}, "goles": {}}
    for f, p in fuentes.items():
        for fam, c in candidatos_resultado(base, p, odds).items():
            familias[fam][f] = c
    # goles: modelos con matriz propia y el mercado invertido a intensidades (ancla de mercado)
    for m in ("a0_xg", "dc_prod"):
        x = base[["match_id"]].merge(pred[pred["modelo"] == m], on="match_id", how="left")
        familias["goles"][m] = candidatos_goles(base, x["lam"], x["mu"], x["rho"].iloc[0])
    rho = float(pred.loc[pred["modelo"] == "dc_prod", "rho"].median())
    ajuste = [market_lambdas(h, dr, a, rho=rho) for h, dr, a in base[["mk_home", "mk_draw", "mk_away"]].to_numpy()]
    familias["goles"]["mercado_anclado"] = candidatos_goles(base, [f.lam for f in ajuste], [f.mu for f in ajuste], rho)
    familias["corners"] = candidatos_conteo(d, "corners", (8.5, 9.5, 10.5), df)
    familias["amarillas"] = candidatos_conteo(d, "yellow", (3.5, 4.5, 5.5), df)

    salida = {}
    for fam, por_fuente in familias.items():
        salida[fam] = {}
        print(f"\n######## {fam}")
        for f, c in por_fuente.items():
            sel = seleccion_diaria(c[c["prob"] > 0])
            cal = calibracion_alta(c.loc[c["prob"] > 0, "prob"], c.loc[c["prob"] > 0, "acierto"])
            salida[fam][f] = {"seleccion": sel.to_dict("records"), "calibracion": cal.to_dict("records")}
            print(f"\n-- {f}\n", sel.round(3).to_string(index=False), "\n", cal.round(3).to_string(index=False))
            if "cuota" in c and c["cuota"].notna().any():
                cc = c[c["cuota"] >= CUOTA_MIN]
                sel2 = seleccion_diaria(cc)
                salida[fam][f]["cuota_min_140"] = sel2.to_dict("records")
                print(f" con cuota >= {CUOTA_MIN}\n", sel2.round(3).to_string(index=False))
    # Mejor pronóstico del día entre TODAS las familias, solo opciones con cuota >= CUOTA_MIN (1X2 y doble con cuota
    # real; goles, córners y tarjetas con tope de probabilidad). Se elige por probabilidad anunciada y se mide lo ocurrido.
    ids = set(base["match_id"])
    def con_cuota(c):
        return c[(c["prob"] > 0) & (c["cuota"].isna() | (c["cuota"] >= CUOTA_MIN))] if "cuota" in c else c[c["prob"] > 0]
    piezas = {"1x2": familias["1x2"]["mercado"], "doble": familias["doble"]["mercado"], "goles": familias["goles"]["a0_xg"],
              "corners": familias["corners"]["c2_yip"], "amarillas": familias["amarillas"]["t3_dawson"]}
    for nombre, usar in {"todas": list(piezas), "sin_doble": ["1x2", "goles", "corners", "amarillas"],
                         "solo_1x2_y_doble": ["1x2", "doble"], "solo_conteos_y_goles": ["goles", "corners", "amarillas"]}.items():
        c = pd.concat([con_cuota(piezas[f])[lambda x: x["match_id"].isin(ids)] for f in usar], ignore_index=True)
        sel = seleccion_diaria(c, coberturas=(0.02, 0.05, 0.1, 0.2))
        reparto = c.assign(rango=c.groupby("dia")["prob"].rank(ascending=False, method="first")).query("rango == 1")["familia"].value_counts().to_dict()
        salida.setdefault("combinado", {})[nombre] = {"seleccion": sel.to_dict("records"), "ganadora_del_dia": reparto,
                                                       "calibracion": calibracion_alta(c["prob"], c["acierto"], (0.5, 0.6, 0.7, 0.8, 0.9, 1.0001)).to_dict("records")}
        print(f"\n######## COMBINADO ({nombre}), cuota >= {CUOTA_MIN}; familia ganadora del día: {reparto}\n",
              sel.round(3).to_string(index=False))
        print(calibracion_alta(c["prob"], c["acierto"], (0.5, 0.6, 0.7, 0.8, 0.9, 1.0001)).round(3).to_string(index=False))
    (d / "metricas_alta_probabilidad.json").write_text(json.dumps(salida, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
