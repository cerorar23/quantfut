"""
Contraste de las hipótesis del titular para mejorar ambos marcan, primera mitad, córners y tarjetas (9-nov-2026).

    ejecutar.sh .local/entreno_AAAAMMDD qf.eval.hipotesis_mercados correr \
        --oos .local/backtest_oos_2024/pit_oos.csv --mercados .local/backtest_mercados --salida .local/hipotesis_mercados

Hipótesis, criterios y reglas: docs/hipotesis_mercados_20261109.md (fijados ANTES de medir). Todo es fuera de muestra y point-in-time:
cada modelo secundario se entrena con filas anteriores al corte y se evalúa en los 28 días siguientes.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from .metrics import diebold_mariano

log = logging.getLogger("hipotesis_mercados")

INICIO = "2025-07-01"
PASO_DIAS = 28
VIDA_RASGOS = 180.0          # semivida (días) de las tasas por equipo
CRITERIOS = {"b1": -0.001, "b2": -0.0005, "liga": 0.005, "t1_gap": 0.03, "t1_n": 100, "k1": -0.001}
PUB_MIN, PUB_MAX = 0.62, 0.85    # rango publicado de la primera mitad desde el 9-nov-2026


# ------------------------------------------------------------------------------------------- utilidades

def _semana(kick) -> np.ndarray:
    k = pd.to_datetime(kick, utc=True)
    return (k.dt.isocalendar().year.astype(str) + "-" + k.dt.isocalendar().week.astype(str)).to_numpy()


def _logit(p):
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def comparar(base: np.ndarray, otra: np.ndarray, kick, ligas) -> dict:
    """Pérdidas por fila (menor es mejor): diferencia media otra − base con IC95 por semana y detalle por liga."""
    base, otra = np.asarray(base, float), np.asarray(otra, float)
    dm = diebold_mariano(otra, base, _semana(pd.Series(kick)))
    por_liga = {}
    ligas = np.asarray(ligas)
    sem = _semana(pd.Series(kick))
    for l in sorted(set(ligas)):
        m = ligas == l
        r = diebold_mariano(otra[m], base[m], sem[m])
        por_liga[l] = {"n": int(m.sum()), "delta": r["delta"], "ic95": list(r["ic95"]),
                       "peor": bool(r["delta"] > CRITERIOS["liga"] and r["ic95"][0] > 0)}
    return {"n": int(len(base)), "delta": dm["delta"], "ic95": list(dm["ic95"]), "por_liga": por_liga,
            "ligas_peores": [l for l, v in por_liga.items() if v["peor"]]}


# ------------------------------------------------------------------------------------------- rasgos previos (H1)

def rasgos_previos(partidos: pd.DataFrame, vida: float = VIDA_RASGOS) -> pd.DataFrame:
    """
    Una fila por partido (índice = match_id) con rasgos conocidos ANTES del saque. `partidos`: match_id, league_id, season, kickoff_utc,
    home_team_id, away_team_id, home_goals, away_goals (terminados). Tasas por equipo con media exponencial (semivida `vida` días):
    «ambos marcan», «no marcar» y portería a cero; y la tabla de la liga (puntos por partido, posición y fase de la temporada).
    El propio partido nunca entra en sus rasgos.
    """
    d = partidos.sort_values(["kickoff_utc", "match_id"]).reset_index(drop=True)
    k = math.log(2.0) / vida
    estado = {}                                   # equipo -> [t_dias, peso, btts, no_marca, porteria_cero]
    tabla = defaultdict(lambda: defaultdict(lambda: [0, 0]))   # (liga, temporada) -> equipo -> [puntos, jugados]
    filas = []
    t0 = d["kickoff_utc"].iloc[0]
    for r in d.itertuples(index=False):
        t = (r.kickoff_utc - t0).total_seconds() / 86400.0
        h, a = r.home_team_id, r.away_team_id

        def tasas(eq):
            s = estado.get(eq)
            if s is None:
                return (np.nan,) * 4
            f = math.exp(-k * (t - s[0]))
            w = s[1] * f
            return (w, s[2] / s[1], s[3] / s[1], s[4] / s[1]) if w >= 2.0 else (np.nan,) * 4  # >= 2 partidos efectivos

        th, ta = tasas(h), tasas(a)
        copa = str(r.league_id).startswith("eu.")
        tb = tabla[(r.league_id, r.season)] if not copa else None
        if tb is not None and len(tb) >= 4:
            ppg = {e: (v[0] / v[1] if v[1] >= 3 else np.nan) for e, v in tb.items()}
            validos = np.sort(np.array([v for v in ppg.values() if v == v]))

            def rank(e):   # 1 = líder: fracción de equipos con puntos por partido iguales o menores
                v = ppg.get(e, np.nan)
                return float(np.searchsorted(validos, v, side="right") / len(validos)) if v == v and len(validos) else np.nan
            equipos = len(tb)
            jug = min(tb[h][1], tb[a][1]) if h in tb and a in tb else 0
            fraccion = min(jug / max(2 * (equipos - 1), 1), 1.0)
            ppg_h, ppg_a = ppg.get(h, np.nan), ppg.get(a, np.nan)
            rk_h, rk_a = rank(h) if h in tb else np.nan, rank(a) if a in tb else np.nan
        else:
            ppg_h = ppg_a = rk_h = rk_a = np.nan
            fraccion = np.nan
        filas.append({"match_id": r.match_id, "peso_h": th[0], "btts_h": th[1], "nomarca_h": th[2], "cero_h": th[3],
                      "peso_a": ta[0], "btts_a": ta[1], "nomarca_a": ta[2], "cero_a": ta[3],
                      "ppg_h": ppg_h, "ppg_a": ppg_a, "rank_h": rk_h, "rank_a": rk_a, "fraccion": fraccion,
                      "tramo_final": float(fraccion >= 0.75) if fraccion == fraccion else np.nan, "copa": float(copa)})
        # actualización con el resultado (después de calcular los rasgos)
        hg, ag = int(r.home_goals), int(r.away_goals)
        btts = float(hg > 0 and ag > 0)
        for eq, marcados, recibidos in ((h, hg, ag), (a, ag, hg)):
            s = estado.get(eq)
            obs = [btts, float(marcados == 0), float(recibidos == 0)]
            if s is None:
                estado[eq] = [t, 1.0, *obs]
            else:
                f = math.exp(-k * (t - s[0]))
                estado[eq] = [t, s[1] * f + 1.0, s[2] * f + obs[0], s[3] * f + obs[1], s[4] * f + obs[2]]
        if tb is not None:
            pts_h, pts_a = (3, 0) if hg > ag else (1, 1) if hg == ag else (0, 3)
            tb[h][0] += pts_h; tb[h][1] += 1
            tb[a][0] += pts_a; tb[a][1] += 1
    return pd.DataFrame(filas).set_index("match_id")


COLUMNAS_H1 = ["lam_log", "mu_log", "btts_h", "btts_a", "nomarca_h", "nomarca_a", "cero_h", "cero_a",
               "ppg_h", "ppg_a", "rank_h", "rank_a", "tramo_final", "copa"]


def prob_btts_dc(lam, mu, rho) -> np.ndarray:
    from ..model.calibration import score_matrices
    out = np.empty(len(lam))
    lam, mu, rho = np.asarray(lam, float), np.asarray(mu, float), np.asarray(rho, float)
    for r in np.unique(np.round(rho, 6)):
        m = np.round(rho, 6) == r
        out[m] = score_matrices(lam[m], mu[m], float(r), 10)[:, 1:, 1:].sum(axis=(1, 2))
    return out


def _ajustar_logistica(X_tr, y_tr, X_te, C=0.5):
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    medias = np.nanmean(X_tr, axis=0)
    medias = np.where(np.isnan(medias), 0.0, medias)
    X_tr, X_te = np.where(np.isnan(X_tr), medias, X_tr), np.where(np.isnan(X_te), medias, X_te)
    esc = StandardScaler().fit(X_tr)
    m = LogisticRegression(C=C, max_iter=500).fit(esc.transform(X_tr), y_tr)
    return m.predict_proba(esc.transform(X_te))[:, 1]


def experimento_h1(oos: pd.DataFrame, rasgos: pd.DataFrame, inicio: str = INICIO, paso: int = PASO_DIAS) -> dict:
    """«Ambos marcan»: base (Dixon-Coles) frente a recalibración básica (log λ, log μ) y modelo completo con rasgos previos."""
    o = oos[oos["both_known"].astype(bool)].copy()
    o["kickoff_utc"] = pd.to_datetime(o["kickoff_utc"], utc=True)
    o = o.join(rasgos, on="match_id", how="inner").sort_values("kickoff_utc").reset_index(drop=True)
    o["y"] = ((o["home_goals"] > 0) & (o["away_goals"] > 0)).astype(float)
    o["lam_log"], o["mu_log"] = np.log(o["lam"]), np.log(o["mu"])
    o["p_dc"] = prob_btts_dc(o["lam"], o["mu"], o["rho"])
    corte, fin = pd.Timestamp(inicio, tz="UTC"), o["kickoff_utc"].max()
    partes = []
    while corte <= fin:
        tr = o[o["kickoff_utc"] < corte]
        te = o[(o["kickoff_utc"] >= corte) & (o["kickoff_utc"] < corte + pd.Timedelta(days=paso))]
        if len(tr) >= 500 and len(te):
            y = tr["y"].to_numpy()
            te = te.assign(p_basica=_ajustar_logistica(tr[["lam_log", "mu_log"]].to_numpy(float), y, te[["lam_log", "mu_log"]].to_numpy(float)),
                           p_completa=_ajustar_logistica(tr[COLUMNAS_H1].to_numpy(float), y, te[COLUMNAS_H1].to_numpy(float)))
            partes.append(te)
        corte += pd.Timedelta(days=paso)
    t = pd.concat(partes, ignore_index=True)
    br = {v: (t[f"p_{v}"] - t["y"]) ** 2 for v in ("dc", "basica", "completa")}
    ll = {v: -(t["y"] * np.log(np.clip(t[f"p_{v}"], 1e-9, 1)) + (1 - t["y"]) * np.log(np.clip(1 - t[f"p_{v}"], 1e-9, 1))) for v in br}
    freq = float(t["y"].mean())
    base_brier = freq * (1 - freq)
    res = {"n": int(len(t)), "frecuencia": freq,
           "brier": {v: float(br[v].mean()) for v in br}, "log_loss": {v: float(ll[v].mean()) for v in ll},
           "skill_brier_vs_frecuencia": {v: float(1 - br[v].mean() / base_brier) for v in br}}
    kk = t["kickoff_utc"]
    res["completa_vs_dc"] = comparar(br["dc"].to_numpy(), br["completa"].to_numpy(), kk, t["league_id"])
    res["completa_vs_basica"] = comparar(br["basica"].to_numpy(), br["completa"].to_numpy(), kk, t["league_id"])
    res["basica_vs_dc"] = comparar(br["dc"].to_numpy(), br["basica"].to_numpy(), kk, t["league_id"])
    b1 = res["completa_vs_dc"]["delta"] <= CRITERIOS["b1"] and res["completa_vs_dc"]["ic95"][1] < 0
    b2 = res["completa_vs_basica"]["delta"] <= CRITERIOS["b2"]
    b3 = not res["completa_vs_dc"]["ligas_peores"]
    res["criterios"] = {"B1": bool(b1), "B2": bool(b2), "B3": bool(b3), "candidato": bool(b1 and b2 and b3)}
    return res


# ------------------------------------------------------------------------------------------- primera mitad (H2)

def experimento_h2(oos: pd.DataFrame, ht: pd.DataFrame, partidos_ht: pd.DataFrame, inicio: str = INICIO,
                   paso: int = PASO_DIAS, ventana_dias: int = 730, prior_goles: float = 400.0) -> dict:
    """Primera mitad: proporción fija (producción) frente a `prop_liga` (24 meses por competición) y `cal_liga` (intercepto por competición)."""
    from ..model import primer_tiempo as m1t
    o = oos[oos["both_known"].astype(bool)].copy()
    o["kickoff_utc"] = pd.to_datetime(o["kickoff_utc"], utc=True)
    o = o.merge(ht, on="match_id", how="inner").dropna(subset=["home_goals_ht", "away_goals_ht"]).sort_values("kickoff_utc").reset_index(drop=True)
    o["y_gol"] = ((o["home_goals_ht"] + o["away_goals_ht"]) > 0).astype(float)
    o["y_amb"] = ((o["home_goals_ht"] > 0) & (o["away_goals_ht"] > 0)).astype(float)
    ph = partidos_ht.copy()
    ph["kickoff_utc"] = pd.to_datetime(ph["kickoff_utc"], utc=True)
    glob = (ph["home_goals_ht"].sum() / max(ph["home_goals"].sum(), 1), ph["away_goals_ht"].sum() / max(ph["away_goals"].sum(), 1))

    def probs_fila(lam, mu, prop):
        p = m1t.probs(lam, mu, prop)
        return p["gol_1t_si"], p["ambos_1t_si"]

    ligas = sorted(o["league_id"].unique())
    dummies = lambda s: np.stack([(s == l).astype(float) for l in ligas], axis=1)
    partes = []
    corte, fin = pd.Timestamp(inicio, tz="UTC"), o["kickoff_utc"].max()
    while corte <= fin:
        tr = o[o["kickoff_utc"] < corte]
        te = o[(o["kickoff_utc"] >= corte) & (o["kickoff_utc"] < corte + pd.Timedelta(days=paso))].copy()
        if len(tr) >= 500 and len(te):
            hist = ph[(ph["kickoff_utc"] < corte) & (ph["kickoff_utc"] >= corte - pd.Timedelta(days=ventana_dias))]
            prop = {}
            for l, g in hist.groupby("league_id"):
                gh, ga = g["home_goals"].sum(), g["away_goals"].sum()
                prop[l] = ((g["home_goals_ht"].sum() + prior_goles * glob[0]) / (gh + prior_goles),
                           (g["away_goals_ht"].sum() + prior_goles * glob[1]) / (ga + prior_goles))
            fijo = [probs_fila(a, b, m1t.PROPORCION_1T) for a, b in zip(te["lam"], te["mu"])]
            lig = [probs_fila(a, b, prop.get(l, m1t.PROPORCION_1T)) for a, b, l in zip(te["lam"], te["mu"], te["league_id"])]
            te["g_fijo"], te["a_fijo"] = [x[0] for x in fijo], [x[1] for x in fijo]
            te["g_prop"], te["a_prop"] = [x[0] for x in lig], [x[1] for x in lig]
            # recalibración con intercepto por competición (entrenada con filas anteriores y las λ/μ ya medidas)
            tr_f = [probs_fila(a, b, m1t.PROPORCION_1T) for a, b in zip(tr["lam"], tr["mu"])]
            for nombre, idx, y in (("g", 0, "y_gol"), ("a", 1, "y_amb")):
                from sklearn.linear_model import LogisticRegression
                Xtr = np.hstack([_logit([f[idx] for f in tr_f])[:, None], dummies(tr["league_id"].to_numpy())])
                Xte = np.hstack([_logit(te[f"{nombre}_fijo"])[:, None], dummies(te["league_id"].to_numpy())])
                te[f"{nombre}_cal"] = LogisticRegression(C=1.0, max_iter=500).fit(Xtr, tr[y]).predict_proba(Xte)[:, 1]
            partes.append(te)
        corte += pd.Timedelta(days=paso)
    t = pd.concat(partes, ignore_index=True)
    res = {"n": int(len(t)), "variantes": {}}
    for v in ("fijo", "prop", "cal"):
        res["variantes"][v] = {
            "brier_gol_1t": float(((t[f"g_{v}"] - t["y_gol"]) ** 2).mean()),
            "brier_ambos_1t": float(((t[f"a_{v}"] - t["y_amb"]) ** 2).mean())}
    # publicados: gol 1T (directo) y ambos 1T «no» (complemento), 0,62-0,85; y, POSTERIOR a los criterios, la franja alta 0,75-0,85,
    # que es donde el backtest de mercados vio el desfase de Liga MX y Champions (el rango completo ya lo cumple la proporción fija)
    for v in ("fijo", "prop", "cal"):
        for clave, (lo, hi) in (("publicados", (PUB_MIN, PUB_MAX)), ("publicados_franja_alta", (0.75, PUB_MAX))):
            lados = []
            for liga, g in t.groupby("league_id"):
                for p, y in ((g[f"g_{v}"], g["y_gol"]), (1 - g[f"a_{v}"], 1 - g["y_amb"])):
                    m = (p >= lo) & (p <= hi)
                    lados.append(pd.DataFrame({"liga": liga, "p": p[m], "y": y[m]}))
            L = pd.concat(lados, ignore_index=True)
            res["variantes"][v][clave] = {
                liga: {"n": int(len(g)), "promesa": float(g["p"].mean() - g["y"].mean()) if len(g) else None}
                for liga, g in L.groupby("liga") if liga in ("mx.liga_mx", "eu.ucl")}
            res["variantes"][v][clave]["todas"] = {"n": int(len(L)), "promesa": float(L["p"].mean() - L["y"].mean())}
    kk = t["kickoff_utc"]
    for v in ("prop", "cal"):
        perdida = lambda s: ((t[f"g_{s}"] - t["y_gol"]) ** 2 + (t[f"a_{s}"] - t["y_amb"]) ** 2).to_numpy() / 2
        res[f"{v}_vs_fijo"] = comparar(perdida("fijo"), perdida(v), kk, t["league_id"])
        pub = res["variantes"][v]["publicados"]
        t1 = all(k in pub and pub[k]["n"] >= CRITERIOS["t1_n"] and abs(pub[k]["promesa"]) <= CRITERIOS["t1_gap"] for k in ("mx.liga_mx", "eu.ucl"))
        t2 = res[f"{v}_vs_fijo"]["delta"] <= 0 and not res[f"{v}_vs_fijo"]["ligas_peores"]
        res[f"criterios_{v}"] = {"T1": bool(t1), "T2": bool(t2), "candidato": bool(t1 and t2)}
    return res


# ------------------------------------------------------------------------------------------- córners y tarjetas (H3)

def _nb_over(mu: np.ndarray, alpha: float, linea: float) -> np.ndarray:
    from scipy.stats import nbinom, poisson
    k = math.floor(linea)
    if alpha < 1e-6:
        return 1.0 - poisson.cdf(k, mu)
    n = 1.0 / alpha
    return 1.0 - nbinom.cdf(k, n, n / (n + mu))


def experimento_h3(tabla: pd.DataFrame, oos: pd.DataFrame, familia: str, lineas: tuple, inicio: str = "2026-01-01", paso: int = PASO_DIAS) -> dict:
    """Apila log del esperado actual (acumulador) y los goles esperados del modelo en una binomial negativa; compara el Brier de las líneas."""
    from sklearn.linear_model import PoissonRegressor
    nombre = f"{familia}_total"
    base = tabla[tabla["mercado"] == nombre][["evento", "liga", "esperado", "real"]].dropna()
    o = oos[oos["both_known"].astype(bool)][["match_id", "kickoff_utc", "league_id", "lam", "mu"]].copy()
    o["kickoff_utc"] = pd.to_datetime(o["kickoff_utc"], utc=True)
    d = base.merge(o, left_on="evento", right_on="match_id", how="inner").sort_values("kickoff_utc").reset_index(drop=True)
    for L in lineas:
        sub = tabla[tabla["mercado"] == f"{familia}_over_{L}"].set_index("evento")["prob"]
        d[f"prod_{L}"] = d["evento"].map(sub)
    d = d.dropna(subset=[f"prod_{L}" for L in lineas])
    d["x1"], d["x2"], d["x3"] = np.log(np.clip(d["esperado"], 0.5, None)), np.log(d["lam"]), np.log(d["mu"])
    d["x4"] = (d["x2"] - d["x3"]).abs()
    cols = ["x1", "x2", "x3", "x4"]
    corte, fin = pd.Timestamp(inicio, tz="UTC"), d["kickoff_utc"].max()
    partes = []
    while corte <= fin:
        tr = d[d["kickoff_utc"] < corte]
        te = d[(d["kickoff_utc"] >= corte) & (d["kickoff_utc"] < corte + pd.Timedelta(days=paso))].copy()
        if len(tr) >= 400 and len(te):
            m = PoissonRegressor(alpha=1e-4, max_iter=500).fit(tr[cols], tr["real"])
            mu_tr = m.predict(tr[cols])
            alpha = max(0.0, float(((tr["real"] - mu_tr) ** 2 - mu_tr).sum() / (mu_tr ** 2).sum()))
            mu_te = m.predict(te[cols])
            for L in lineas:
                te[f"nb_{L}"] = _nb_over(mu_te, alpha, L)
            partes.append(te)
        corte += pd.Timedelta(days=paso)
    t = pd.concat(partes, ignore_index=True)
    res = {"n": int(len(t)), "lineas": {}}
    perd_prod, perd_nb = np.zeros(len(t)), np.zeros(len(t))
    for L in lineas:
        y = (t["real"] > L).astype(float)
        bp, bn = (t[f"prod_{L}"] - y) ** 2, (t[f"nb_{L}"] - y) ** 2
        res["lineas"][str(L)] = {"brier_prod": float(bp.mean()), "brier_apilado": float(bn.mean())}
        perd_prod += bp.to_numpy() / len(lineas)
        perd_nb += bn.to_numpy() / len(lineas)
    res["apilado_vs_acumulador"] = comparar(perd_prod, perd_nb, t["kickoff_utc"], t["league_id"])
    res["criterio_K1"] = bool(res["apilado_vs_acumulador"]["delta"] <= CRITERIOS["k1"] and res["apilado_vs_acumulador"]["ic95"][1] < 0)
    return res


# ------------------------------------------------------------------------------------------- orquestación

def cargar_partidos() -> pd.DataFrame:
    from ..db import query
    df = pd.DataFrame(query("""SELECT match_id, league_id, season, kickoff_utc, home_team_id, away_team_id, home_goals, away_goals,
                                      home_goals_ht, away_goals_ht
                               FROM matches WHERE status = 'finished' AND home_goals IS NOT NULL AND away_goals IS NOT NULL
                                 AND kickoff_utc >= '2019-07-01' ORDER BY kickoff_utc, match_id"""))
    df["kickoff_utc"] = pd.to_datetime(df["kickoff_utc"], utc=True)
    return df


def correr(oos_csv: Path, mercados: Path, salida: Path, solo: str | None = None) -> dict:
    oos = pd.read_csv(oos_csv, parse_dates=["kickoff_utc"])
    partidos = cargar_partidos()
    log.info("partidos %d, oos %d", len(partidos), len(oos))
    rasgos = rasgos_previos(partidos)
    salida.mkdir(parents=True, exist_ok=True)
    previo = salida / "hipotesis.json"
    res = json.loads(previo.read_text(encoding="utf-8")) if solo and previo.exists() else {"inicio": INICIO, "criterios": CRITERIOS}
    if solo in (None, "h1"):
        res["h1"] = experimento_h1(oos, rasgos)
        log.info("H1 hecho")
    if solo in (None, "h2"):
        ht = partidos[["match_id", "home_goals_ht", "away_goals_ht"]]
        res["h2"] = experimento_h2(oos, ht, partidos.dropna(subset=["home_goals_ht", "away_goals_ht"]))
        log.info("H2 hecho")
    if solo in (None, "h3"):
        res["h3"] = {}
        for fam, lineas, archivo in (("corners", (8.5, 9.5, 10.5), "tabla_corners.csv.gz"), ("cards", (3.5, 4.5, 5.5), "tabla_tarjetas.csv.gz")):
            tabla = pd.read_csv(mercados / archivo)
            res["h3"][fam] = experimento_h3(tabla, oos, fam, lineas)
    previo.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return res


def main(argv=None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("correr")
    c.add_argument("--oos", default=".local/backtest_oos_2024/pit_oos.csv")
    c.add_argument("--mercados", default=".local/backtest_mercados")
    c.add_argument("--salida", default=".local/hipotesis_mercados")
    c.add_argument("--solo", choices=("h1", "h2", "h3"), help="rehace solo una hipótesis y conserva el resto del JSON")
    a = ap.parse_args(argv)
    r = correr(Path(a.oos), Path(a.mercados), Path(a.salida), a.solo)
    print(json.dumps({"h1": r["h1"]["criterios"], "h2": {k: v for k, v in r["h2"].items() if k.startswith("criterios")},
                      "h3": {f: x["criterio_K1"] for f, x in r["h3"].items()}}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
