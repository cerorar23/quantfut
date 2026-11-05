# apps/tennis/ops/linea_base_walkforward.py
"""Línea base walk-forward (origen móvil por temporadas) sobre Tennis-Data, con el cierre de Pinnacle como referencia.

Modelos INDEPENDIENTES del motor actual (implementación propia): 50/50, ranking logístico, Elo, Elo+superficie, Elo recalibrado
con temporadas previas. Referencia: probabilidad sin margen (proporcional) de Pinnacle (PS) y, aparte, B365 y media (Avg).
Reglas: el Elo se actualiza por bloques de fecha (nunca se usa un partido de la misma fecha para predecirlo); la logística de
ranking y la recalibración se ajustan SOLO con temporadas anteriores a la evaluada; la presentación A/B es aleatoria (semilla fija).

Uso:  python -I apps/tennis/ops/linea_base_walkforward.py [--desde 2019] [--salida DIR]
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

import linea_base_datos as ld

SEMILLA = 20261104
K = 24.0
SALIDA_DATOS = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\rediseno_20261104")
# Las tablas pequeñas se copian después a docs/tenis_auditoria_tablas/ (el sandbox del shell no escribe en el worktree).
SALIDA_TABLAS = SALIDA_DATOS / "tablas"


def elo_walk(d: pd.DataFrame) -> pd.DataFrame:
    """Predicción pre-partido de Elo general y Elo+superficie, actualizando por bloques de fecha. Devuelve p(ganador real)."""
    gen, sup, n = defaultdict(lambda: 1500.0), defaultdict(lambda: 1500.0), defaultdict(int)
    p_gen, p_mix, hist = np.empty(len(d)), np.empty(len(d)), np.empty(len(d))
    for _, bloque in d.groupby("Date", sort=True):
        dg, ds = defaultdict(float), defaultdict(float)
        for i, r in zip(bloque.index, bloque.itertuples()):
            w, l, s = r.kw, r.kl, r.Surface
            dif = gen[w] - gen[l]
            p_gen[i] = 1 / (1 + 10 ** (-dif / 400))
            difs = sup[(w, s)] - sup[(l, s)]
            p_mix[i] = 1 / (1 + 10 ** (-(dif + difs) / 800))
            hist[i] = min(n[w], n[l])
            ps = 1 / (1 + 10 ** (-difs / 400))
            dg[w] += K * (1 - p_gen[i]); dg[l] -= K * (1 - p_gen[i])
            ds[(w, s)] += K * (1 - ps); ds[(l, s)] -= K * (1 - ps)
        for k, v in dg.items():
            gen[k] += v
        for k, v in ds.items():
            sup[k] += v
        for r in bloque.itertuples():
            n[r.kw] += 1; n[r.kl] += 1
    return pd.DataFrame({"p_elo": p_gen, "p_elo_sup": p_mix, "hist_min": hist}, index=d.index)


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def metricas(y, p):
    p = np.clip(np.asarray(p, float), 1e-8, 1 - 1e-8)
    y = np.asarray(y, float)
    return {"n": len(y), "brier": float(np.mean((p - y) ** 2)),
            "logloss": float(-np.mean(y * np.log(p) + (1 - y) * np.log1p(-p))),
            "acierto": float(np.mean((p >= 0.5) == (y == 1)))}


def calibracion(y, p, rng, reps=300):
    """Pendiente e intercepto de y ~ logit(p) con IC bootstrap por partido."""
    x, y = logit(np.asarray(p)).reshape(-1, 1), np.asarray(y)
    def aj(ix):
        m = LogisticRegression(C=1e6, max_iter=500).fit(x[ix], y[ix])
        return m.coef_[0, 0], m.intercept_[0]
    base = aj(np.arange(len(y)))
    bs = np.array([aj(rng.integers(len(y), size=len(y))) for _ in range(reps)])
    lo, hi = np.quantile(bs[:, 0], [0.025, 0.975])
    return {"pendiente": base[0], "pend_lo": lo, "pend_hi": hi, "intercepto": base[1]}


def perdida(y, p):
    p = np.clip(np.asarray(p, float), 1e-8, 1 - 1e-8)
    return -(y * np.log(p) + (1 - y) * np.log1p(-p))


def dif_bootstrap(y, p_mod, p_ref, rng, reps=2000):
    """Diferencia de log-loss (modelo - referencia) con IC95 bootstrap por partido y varianza para combinar orígenes."""
    dl = perdida(y, p_mod) - perdida(y, p_ref)
    db = (np.asarray(y) - p_mod) ** 2 - (np.asarray(y) - p_ref) ** 2
    idx = rng.integers(len(dl), size=(reps, len(dl)))
    m = dl[idx].mean(axis=1)
    return {"dif_logloss": dl.mean(), "lo": np.quantile(m, 0.025), "hi": np.quantile(m, 0.975), "var": m.var(),
            "dif_brier": db.mean(), "n": len(dl)}


def construir(circuito: str, desde: int):
    d = ld.cargar(circuito, 2005)
    d = d.join(elo_walk(d))
    rng = np.random.default_rng(SEMILLA)
    d["a_gana"] = rng.integers(2, size=len(d))   # presentación aleatoria
    # Cuota/probabilidad de mercado desde la perspectiva del ganador real
    for casa, (cw, cl) in {"ps": ("PSW", "PSL"), "b365": ("B365W", "B365L"), "avg": ("AvgW", "AvgL")}.items():
        d[f"m_{casa}"] = ld.desvig_proporcional(d[cw], d[cl])           # prob. del ganador real
        d[f"margen_{casa}"] = ld.margen(d[cw], d[cl])
    d["anio"] = d["Date"].dt.year
    d["x_rank"] = np.log(d["LRank"]) - np.log(d["WRank"])               # >0: el ganador estaba mejor rankeado
    d["x_pts"] = np.log(d["WPts"].clip(lower=1)) - np.log(d["LPts"].clip(lower=1))
    return d


def ajustar_rank(d, anio):
    """Logística sin intercepto sobre antisimetría (A vs B), ajustada solo con años < anio (y >= 2010)."""
    tr = d[(d.anio < anio) & (d.anio >= 2010) & d.liquidable & d.x_rank.notna() & d.x_pts.notna()]
    X = np.vstack([np.c_[tr.x_rank, tr.x_pts], -np.c_[tr.x_rank, tr.x_pts]])
    y = np.r_[np.ones(len(tr)), np.zeros(len(tr))]
    return LogisticRegression(C=1e6, fit_intercept=False, max_iter=500).fit(X, y)


def predicciones(d, anios):
    """Una fila por partido de los años evaluados, con la probabilidad de cada modelo para el GANADOR real."""
    salida = []
    for anio in anios:
        ev = d[(d.anio == anio) & d.liquidable].copy()
        m_rank = ajustar_rank(d, anio)
        ok = ev.x_rank.notna() & ev.x_pts.notna()
        ev["p_rank"] = np.nan
        ev.loc[ok, "p_rank"] = m_rank.predict_proba(np.c_[ev.loc[ok, "x_rank"], ev.loc[ok, "x_pts"]])[:, 1]
        # Elo recalibrado con las predicciones OOS de temporadas previas (nunca la evaluada)
        pr = d[(d.anio < anio) & (d.anio >= 2012) & d.liquidable]
        # orientación: cada partido aporta (x=logit p, y=1) y su espejo (x=-logit p, y=0)
        X = np.r_[logit(pr.p_elo.values), -logit(pr.p_elo.values)].reshape(-1, 1)
        y = np.r_[np.ones(len(pr)), np.zeros(len(pr))]
        cal = LogisticRegression(C=1e6, fit_intercept=False, max_iter=500).fit(X, y)
        ev["p_elo_cal"] = cal.predict_proba(logit(ev.p_elo.values).reshape(-1, 1))[:, 1]
        ev["escala_cal"] = cal.coef_[0, 0]
        ev["p_50"] = 0.5
        salida.append(ev)
    return pd.concat(salida)


MODELOS = ["p_50", "p_rank", "p_elo", "p_elo_sup", "p_elo_cal"]


def orientar(df, col):
    """Probabilidad de A (presentación aleatoria) y resultado y (A gana)."""
    p = np.where(df.a_gana == 1, df[col], 1 - df[col])
    return df.a_gana.to_numpy(), p


def tablas(ev, circuito, rng):
    filas_met, filas_dif = [], []
    for anio, g in ev.groupby("anio"):
        comun = g[g.m_ps.notna()]
        for mod in MODELOS + ["m_ps", "m_b365", "m_avg"]:
            sub = comun if mod in MODELOS or mod == "m_ps" else g[g[mod].notna()]
            sub = sub[sub[mod].notna()]
            if len(sub) < 50:
                continue
            y, p = orientar(sub, mod)
            filas_met.append(dict(circuito=circuito, origen=anio, modelo=mod, **metricas(y, p), **calibracion(y, p, rng, 150)))
        for mod in MODELOS + ["m_b365", "m_avg"]:
            sub = comun[comun[mod].notna()]
            if len(sub) < 50:
                continue
            y, pm = orientar(sub, mod)
            _, pr = orientar(sub, "m_ps")
            filas_dif.append(dict(circuito=circuito, origen=anio, modelo=mod, ref="m_ps", **dif_bootstrap(y, pm, pr, rng)))
    return pd.DataFrame(filas_met), pd.DataFrame(filas_dif)


def combinar(dif):
    """Combina orígenes ponderando por la inversa de la varianza bootstrap."""
    filas = []
    for (circ, mod), g in dif.groupby(["circuito", "modelo"]):
        w = 1 / g["var"].clip(lower=1e-12)
        m = float((w * g.dif_logloss).sum() / w.sum()); se = float(np.sqrt(1 / w.sum()))
        filas.append(dict(circuito=circ, modelo=mod, origenes=len(g), n=int(g.n.sum()), dif_logloss=m, lo=m - 1.96 * se, hi=m + 1.96 * se))
    return pd.DataFrame(filas)


def segmentos(ev, circuito, rng):
    """Dónde falla: Elo+superficie y Elo calibrado frente al cierre, por segmento (todos los orígenes evaluados juntos)."""
    ev = ev[ev.m_ps.notna()].copy()
    ev["fav_bin"] = pd.cut(np.maximum(ev.m_ps, 1 - ev.m_ps), [0.5, 0.6, 0.7, 0.8, 1.0], include_lowest=True).astype(str)
    ev["best_of_"] = ev["Best of"].astype("Int64").astype(str)
    ev["historia"] = np.where(ev.hist_min < 20, "<20 partidos previos", ">=20")
    filas = []
    for var in ["Surface", "nivel", "Round", "best_of_", "fav_bin", "historia", "indoor", "retirada"]:
        for val, g in ev.groupby(var):
            if len(g) < 200:
                continue
            for mod in ["p_elo_sup", "p_elo_cal"]:
                y, pm = orientar(g, mod); _, pr = orientar(g, "m_ps")
                r = dif_bootstrap(y, pm, pr, rng, 500)
                filas.append(dict(circuito=circuito, variable=var, valor=str(val), modelo=mod, ll_modelo=metricas(y, pm)["logloss"],
                                  ll_cierre=metricas(y, pr)["logloss"], **{k: r[k] for k in ("dif_logloss", "lo", "hi", "n")}))
    return pd.DataFrame(filas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", type=int, default=2019)
    a = ap.parse_args()
    SALIDA_TABLAS.mkdir(parents=True, exist_ok=True); SALIDA_DATOS.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEMILLA + 1)
    todo_m, todo_d, todo_s = [], [], []
    for circ in ("ATP", "WTA"):
        d = construir(circ, a.desde)
        ev = predicciones(d, range(a.desde, int(d.anio.max()) + 1))
        ev.to_parquet(SALIDA_DATOS / f"linea_base_pred_{circ}.parquet")
        m, dif = tablas(ev, circ, rng)
        todo_m.append(m); todo_d.append(dif); todo_s.append(segmentos(ev, circ, rng))
        print(circ, "partidos evaluados:", len(ev), "con cierre PS:", int(ev.m_ps.notna().sum()))
    m, dif, seg = pd.concat(todo_m), pd.concat(todo_d), pd.concat(todo_s)
    m.to_csv(SALIDA_TABLAS / "linea_base_metricas_por_origen.csv", index=False)
    dif.to_csv(SALIDA_TABLAS / "linea_base_dif_vs_cierre_por_origen.csv", index=False)
    combinar(dif).to_csv(SALIDA_TABLAS / "linea_base_dif_vs_cierre_combinada.csv", index=False)
    seg.to_csv(SALIDA_TABLAS / "linea_base_segmentos.csv", index=False)
    print(json.dumps({"semilla": SEMILLA, "K_elo": K, "origenes": f"{a.desde}..max"}))


if __name__ == "__main__":
    main()
