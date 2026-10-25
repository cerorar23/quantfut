"""Auditoría 24-oct: métricas fuera de muestra del Motor A frente al cierre de Pinnacle.

Todo lo que se ajusta (calibración, peso de la mezcla) se estima SOLO con partidos
anteriores al bloque mensual que se evalúa (expanding window). Las apuestas se hacen
al precio de cierre de Pinnacle CON margen.
"""
import sys
import numpy as np
import pandas as pd

D = sys.argv[1]
wf = pd.read_pickle(f"{D}/wf_prodnuevo.pkl")
oos22 = pd.read_pickle(f"{D}/oos_2026.10.22-185314.pkl")
px = pd.read_csv(f"{D}/pinnacle_close.csv", parse_dates=["kickoff_utc", "xg_recorded_at"])

EPS = 1e-12
P = ["p_home", "p_draw", "p_away"]
M = ["mk_home", "mk_draw", "mk_away"]


def metricas(p, y):
    p = np.clip(p, EPS, 1)
    oh = np.eye(3)[y]
    cp, co = np.cumsum(p, 1)[:, :2], np.cumsum(oh, 1)[:, :2]
    rps = ((cp - co) ** 2).sum(1) / 2
    ll = -np.log(p[np.arange(len(y)), y])
    brier = ((p - oh) ** 2).sum(1)
    return rps, ll, brier


def ece(p, y, bins=10):
    # ECE "top-label" + por clase (one-vs-rest) promediado
    out = []
    for k in range(3):
        pk, yk = p[:, k], (y == k).astype(float)
        idx = np.minimum((pk * bins).astype(int), bins - 1)
        e = sum(abs(pk[idx == b].mean() - yk[idx == b].mean()) * (idx == b).mean()
                for b in range(bins) if (idx == b).any())
        out.append(e)
    return float(np.mean(out))


def boot_ci(diff, groups, n=2000, seed=7):
    rng = np.random.default_rng(seed)
    g = pd.Series(diff).groupby(np.asarray(groups))
    sums, cnts = g.sum().to_numpy(), g.count().to_numpy()
    k = len(sums)
    res = []
    for _ in range(n):
        s = rng.integers(0, k, k)
        res.append(sums[s].sum() / cnts[s].sum())
    return np.percentile(res, [2.5, 97.5])


def temp_fit(p, y):
    """Escalado de temperatura multinomial sobre log-prob (1 parámetro)."""
    lp = np.log(np.clip(p, EPS, 1))
    best, bt = 1e9, 1.0
    for t in np.linspace(0.6, 1.6, 101):
        z = lp / t
        q = np.exp(z - z.max(1, keepdims=True)); q /= q.sum(1, keepdims=True)
        v = -np.log(q[np.arange(len(y)), y]).mean()
        if v < best:
            best, bt = v, t
    return bt


def apply_temp(p, t):
    z = np.log(np.clip(p, EPS, 1)) / t
    q = np.exp(z - z.max(1, keepdims=True))
    return q / q.sum(1, keepdims=True)


def blend(pm, pk, w):
    """Mezcla log-lineal (pool logarítmico) modelo/mercado, w = peso del modelo."""
    z = w * np.log(np.clip(pm, EPS, 1)) + (1 - w) * np.log(np.clip(pk, EPS, 1))
    q = np.exp(z - z.max(1, keepdims=True))
    return q / q.sum(1, keepdims=True)


def blend_fit(pm, pk, y):
    best, bw = 1e9, 0.0
    for w in np.linspace(0, 1, 51):
        q = blend(pm, pk, w)
        v = -np.log(q[np.arange(len(y)), y]).mean()
        if v < best:
            best, bw = v, w
    return bw


def rolling_layers(df, min_hist=1500):
    """Calibración por temperatura y peso de mezcla, ajustados solo con el pasado."""
    df = df.sort_values("kickoff_utc").reset_index(drop=True)
    mes = df["kickoff_utc"].dt.to_period("M")
    pc = np.full((len(df), 3), np.nan)
    pb = np.full((len(df), 3), np.nan)
    temps, ws = [], []
    for m in mes.unique():
        te = (mes == m).to_numpy()
        tr = (df["kickoff_utc"] < df.loc[te, "kickoff_utc"].min()).to_numpy()
        if tr.sum() < min_hist:
            continue
        ptr, ytr = df.loc[tr, P].to_numpy(), df.loc[tr, "outcome"].to_numpy()
        t = temp_fit(ptr, ytr)
        w = blend_fit(ptr, df.loc[tr, M].to_numpy(), ytr)
        temps.append((str(m), t)); ws.append((str(m), w))
        pc[te] = apply_temp(df.loc[te, P].to_numpy(), t)
        pb[te] = blend(df.loc[te, P].to_numpy(), df.loc[te, M].to_numpy(), w)
    return df, pc, pb, temps, ws


def kelly_backtest(df, pmod, frac=0.25, edge_min=0.0, cap=0.05):
    """Una apuesta por partido (mayor EV) si p_model > p_mercado y EV>edge_min al precio Pinnacle CON margen."""
    odds = df[["ph", "pd", "pa"]].to_numpy()
    pk = df[M].to_numpy()
    y = df["outcome"].to_numpy()
    bank, stakes, pnl_flat, n = 1.0, [], [], 0
    traj = []
    rows = []
    for i in range(len(df)):
        ev = pmod[i] * odds[i] - 1
        ok = (pmod[i] > pk[i]) & (ev > edge_min)
        if not ok.any():
            continue
        k = int(np.argmax(np.where(ok, ev, -9)))
        b = odds[i, k] - 1
        f = max(0.0, (pmod[i, k] * b - (1 - pmod[i, k])) / b) * frac
        f = min(f, cap)
        win = y[i] == k
        r_flat = b if win else -1.0
        stake = f * bank
        bank += stake * (b if win else -1.0)
        rows.append((df["kickoff_utc"].iloc[i], k, odds[i, k], pmod[i, k], pk[i, k], f, r_flat, win))
        traj.append(bank)
    t = pd.DataFrame(rows, columns=["kickoff", "sel", "odds", "p_mod", "p_mk", "f", "r_flat", "win"])
    if t.empty:
        return {"n": 0}
    day = t["kickoff"].dt.date
    lo, hi = boot_ci(t["r_flat"].to_numpy(), day)
    peak = np.maximum.accumulate(np.r_[1.0, traj])
    dd = float((1 - np.r_[1.0, traj] / peak).max())
    return {"n": len(t), "roi_plano": t["r_flat"].mean(), "roi_ic95": (lo, hi),
            "acierto": t["win"].mean(), "cuota_media": t["odds"].mean(),
            "edge_medio_vs_mercado": (t["p_mod"] - t["p_mk"]).mean(),
            "banca_final_kelly": bank, "max_drawdown": dd}


def informe(nombre, df):
    df = df.merge(px[["match_id", "ph", "pd", "pa", "src", "xg_recorded_at"]], on="match_id", how="left")
    df = df.dropna(subset=M + ["ph", "pd", "pa"]).copy()
    df = df[df["outcome"].between(0, 2)]
    df, pc, pb, temps, ws = rolling_layers(df)
    y = df["outcome"].to_numpy()
    valid = ~np.isnan(pc[:, 0])
    out = {"n": len(df), "desde": str(df["kickoff_utc"].min().date()), "hasta": str(df["kickoff_utc"].max().date()),
           "n_capas": int(valid.sum())}
    grp = df["kickoff_utc"].dt.date.to_numpy()
    res = {}
    cand = {"Mercado (Pinnacle Shin)": df[M].to_numpy(), "Motor A (DC)": df[P].to_numpy(),
            "A calibrado (T, pasado)": pc, "Mezcla A+mercado (pasado)": pb}
    for k, p in cand.items():
        r, l, b = metricas(p[valid], y[valid])
        res[k] = dict(rps=r.mean(), logloss=l.mean(), brier=b.mean(), ece=ece(p[valid], y[valid]))
    r_m, l_m, _ = metricas(df[M].to_numpy()[valid], y[valid])
    r_a, l_a, _ = metricas(df[P].to_numpy()[valid], y[valid])
    r_b, l_b, _ = metricas(pb[valid], y[valid])
    out["dRPS A-mercado IC95"] = boot_ci(r_a - r_m, grp[valid])
    out["dRPS mezcla-mercado IC95"] = boot_ci(r_b - r_m, grp[valid])
    out["dLL mezcla-mercado IC95"] = boot_ci(l_b - l_m, grp[valid])
    out["metricas"] = res
    out["temperaturas (ultimas 3)"] = temps[-3:]
    out["pesos mezcla (ultimos 3)"] = ws[-3:]
    sub = df[valid].reset_index(drop=True)
    out["kelly_A"] = kelly_backtest(sub, df[P].to_numpy()[valid])
    out["kelly_A_edge3"] = kelly_backtest(sub, df[P].to_numpy()[valid], edge_min=0.03)
    out["kelly_mezcla"] = kelly_backtest(sub, pb[valid])
    # por liga
    lig = []
    for lg, g in sub.groupby("league_id"):
        idx = g.index.to_numpy()
        ra, la, _ = metricas(df[P].to_numpy()[valid][idx], y[valid][idx])
        rm, lm, _ = metricas(df[M].to_numpy()[valid][idx], y[valid][idx])
        lig.append((lg, len(idx), ra.mean() - rm.mean(), la.mean() - lm.mean()))
    out["por_liga (n, dRPS, dLL) A-mercado"] = sorted(lig, key=lambda x: x[2])
    # fiabilidad del local
    bins = pd.cut(df[P[0]][valid], [0, .2, .3, .4, .5, .6, .7, .8, 1])
    rel = pd.DataFrame({"p": df[P[0]][valid].to_numpy(), "y": (y[valid] == 0)}).groupby(bins.to_numpy(), observed=True).agg(
        n=("p", "size"), prometido=("p", "mean"), real=("y", "mean"))
    out["fiabilidad local (A)"] = rel.round(3).to_dict("index")
    print(f"\n######## {nombre}")
    for k, v in out.items():
        if isinstance(v, dict) and k == "metricas":
            print("metricas:")
            for m, d in v.items():
                print(f"  {m:28s} RPS {d['rps']:.5f}  LL {d['logloss']:.5f}  Brier {d['brier']:.5f}  ECE {d['ece']:.4f}")
        elif isinstance(v, list) and k.startswith("por_liga"):
            print(k)
            for t in v:
                print(f"  {t[0]:22s} n={t[1]:5d} dRPS {t[2]:+.5f} dLL {t[3]:+.5f}")
        else:
            print(f"{k}: {v}")
    # fugas
    chk = df.rename(columns={"ph": "odds_home"})
    late = (chk["xg_recorded_at"] > chk["kickoff_utc"] + pd.Timedelta(hours=6)).mean()
    print(f"fugas: xG de ESTE partido registrado >6h tras el inicio (normal: es el resultado; no entra a su propia predicción): {late:.1%}")
    print("fugas: kickoff duplicados:", f"{chk['kickoff_utc'].duplicated().mean():.1%}")
    print("fuente del cierre:", df["src"].value_counts().to_dict())


informe("Walk-forward configuración de producción (wf_prodnuevo, 2024-01 → 2026-10)", wf)
informe("Validación del modelo activo 2026.10.22 (último año)", oos22)
