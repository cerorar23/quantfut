"""
F5 del rediseño (A4-A6 en su versión medible con la data de hoy): ¿el once que sale a jugar mueve los goles esperados
más allá de A0 (Dixon-Coles con xG)?

    PYTHONPATH=src python scripts/rediseno_futbol/once_a4.py --datos .local/rediseno_20261101b --pred .local/rediseno_20261101

Tres rasgos por equipo y partido, todos con información ANTERIOR al partido salvo el once, que se toma como el once real
(el once se publica ≈ 60 min antes del saque; en la historia no hay captura previa, así que el once real es la mejor
aproximación y puede traer algún cambio de última hora):
  A4  fuerza del once: suma de los goles esperados de sus once (tasa por 90 de cada jugador con partidos anteriores,
      encogida a su posición, por minutos esperados; `eval/rediseno_jugadores`) frente a la media móvil de ese equipo;
  A5  rotación: titulares de ayer que no están hoy entre los once del partido anterior (0-11);
  A6  bajas de habituales: jugadores que empezaron ≥ 3 de los últimos 5 partidos y hoy no están entre los once (0-5).
  A3  definición y portero: media móvil de (goles − xG) del equipo y de (xGOT recibido − goles encajados) del portero rival
      (el xGOT solo existe en ≈ 22 % de los partidos: se evalúa en esa parte, frente a A0 en las mismas filas);
  A7  entrenador nuevo: el equipo cambió de entrenador en sus últimos 5 partidos (propio y del rival).
Se ajusta una regresión de Poisson con desplazamiento log(λ de A0) y se mide en walk-forward (cada 28 días, desde 2025-01)
si el 1X2 mejora (log-loss, Diebold-Mariano por semanas), siempre frente a A0 en las MISMAS filas.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from qf.eval import rediseno as R
from qf.eval import rediseno_jugadores as J
from qf.eval.metrics import diebold_mariano
from qf.model.calibration import probs_1x2

EVAL = "2024-07-01"
DESDE = pd.Timestamp("2025-01-01", tz="UTC")


def poisson_offset(X: np.ndarray, y: np.ndarray, off: np.ndarray, ridge: float = 1.0, it: int = 30):
    """Regresión de Poisson con desplazamiento (IRLS); devuelve coeficientes y errores estándar."""
    X1 = np.column_stack([np.ones(len(X)), X])
    b = np.zeros(X1.shape[1])
    pen = np.diag([0.0] + [ridge] * X.shape[1])
    for _ in range(it):
        mu = np.exp(np.clip(off + X1 @ b, -10, 10))
        grad = X1.T @ (y - mu) - pen @ b
        hess = (X1 * mu[:, None]).T @ X1 + pen
        paso = np.linalg.solve(hess, grad)
        b += paso
        if np.abs(paso).max() < 1e-8:
            break
    mu = np.exp(np.clip(off + X1 @ b, -10, 10))
    cov = np.linalg.inv((X1 * mu[:, None]).T @ X1 + pen)
    return b, np.sqrt(np.diag(cov))


def rasgos_once(jt: pd.DataFrame, partidos: pd.DataFrame) -> pd.DataFrame:
    """Una fila por (partido, lado) con atk_xi, rotacion, ausentes_habituales (solo con once conocido)."""
    st = jt[jt["titular"]].copy()
    equipos = pd.concat([
        partidos[["match_id", "kickoff_utc", "home_team_id"]].rename(columns={"home_team_id": "team_id"}).assign(side="home"),
        partidos[["match_id", "kickoff_utc", "away_team_id"]].rename(columns={"away_team_id": "team_id"}).assign(side="away")])
    atk = st.groupby(["match_id", "side"])["m_gol"].sum().rename("atk_xi")
    n11 = st.groupby(["match_id", "side"]).size().rename("n_once")
    once = st.groupby(["match_id", "side"])["jugador_id"].apply(frozenset).rename("once")
    x = equipos.join(pd.concat([atk, n11, once], axis=1), on=["match_id", "side"])
    x = x[x["n_once"].ge(10)].sort_values(["team_id", "kickoff_utc"]).reset_index(drop=True)
    g = x.groupby("team_id")
    x["base_atk"] = g["atk_xi"].transform(lambda s: s.ewm(halflife=10, ignore_na=True).mean().shift(1))
    previo = g["once"].shift(1)
    x["rotacion"] = [len(a - b) if isinstance(b, frozenset) else np.nan for a, b in zip(x["once"], previo)]
    ausentes = []
    for _, h in g:
        hist = list(h["once"])
        for i, a in enumerate(hist):
            ult = hist[max(0, i - 5):i]
            if len(ult) < 3:
                ausentes.append(np.nan); continue
            cuenta = pd.Series([p for s in ult for p in s]).value_counts()
            habituales = set(cuenta[cuenta >= 3].index)
            ausentes.append(len(habituales - a))
    # el bucle recorre los equipos en el orden de groupby: se reasigna por índice
    idx = np.concatenate([h.index.to_numpy() for _, h in g])
    x["ausentes"] = np.nan
    x.loc[idx, "ausentes"] = ausentes
    x["x_atk"] = np.log((x["atk_xi"] / x["base_atk"]).clip(0.3, 3.0))
    return x[["match_id", "side", "x_atk", "rotacion", "ausentes"]]


def rasgos_equipo(partidos: pd.DataFrame, contexto: pd.DataFrame) -> pd.DataFrame:
    """A3 y A7 por (partido, lado), con información anterior al partido."""
    c = contexto.set_index("match_id")
    filas = []
    for lado, rival in (("home", "away"), ("away", "home")):
        filas.append(pd.DataFrame({
            "match_id": partidos["match_id"], "side": lado, "kickoff_utc": partidos["kickoff_utc"],
            "team_id": partidos[f"{lado}_team_id"], "gf": partidos[f"{lado}_goals"], "xgf": partidos[f"{lado}_xg"],
            "ga": partidos[f"{rival}_goals"], "xgot_faced": partidos[f"{rival}_xgot"],
            "coach": partidos["match_id"].map(c[f"entrenador_{'local' if lado == 'home' else 'visita'}"])}))
    x = pd.concat(filas).sort_values(["team_id", "kickoff_utc"]).reset_index(drop=True)
    g = x.groupby("team_id")
    x["dif_fin"] = x["gf"] - x["xgf"]
    x["dif_gk"] = x["xgot_faced"] - x["ga"]
    for col, mitad, nombre in (("dif_fin", 20, "fin"), ("dif_gk", 30, "gk")):
        media = g[col].transform(lambda s: s.ewm(halflife=mitad, ignore_na=True).mean().shift(1))
        n = g[col].transform(lambda s: s.notna().cumsum().shift(1))
        x[nombre] = media.where(n >= 10)
    previo = g["coach"].shift(1)
    cambio = (x["coach"] != previo) & previo.notna() & x["coach"].notna()
    x["cambio_id"] = cambio.groupby(x["team_id"]).cumsum()
    desde = x.groupby(["team_id", "cambio_id"]).cumcount()
    x["nuevo"] = ((x["cambio_id"] > 0) & (desde < 5)).astype(float)
    return x[["match_id", "side", "fin", "gk", "nuevo"]]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", default=".local/rediseno_20261101b")
    ap.add_argument("--pred", default=".local/rediseno_20261101")
    a = ap.parse_args()
    d, dp = Path(a.datos), Path(a.pred)
    datos = R.cargar(d)
    df = R.tabla_partidos(datos)
    partidos = pd.read_csv(d / "partidos.csv.gz", parse_dates=["kickoff_utc"])
    jug = pd.read_csv(d / "jugadores.csv.gz", low_memory=False)
    jt = J.previos(J.tabla(jug, df, datos.incidencias), EVAL)
    f = rasgos_once(jt, partidos)
    print(f"once conocido en {f['match_id'].nunique()} partidos; rotación media {f['rotacion'].mean():.2f}, "
          f"habituales ausentes {f['ausentes'].mean():.2f}")

    pred = pd.read_csv(dp / "pred_f3.csv.gz").query("modelo == 'a0_xg'").set_index("match_id")
    base = partidos.merge(pred[["lam", "mu", "rho"]], left_on="match_id", right_index=True)
    base = base[base["kickoff_utc"] >= pd.Timestamp(EVAL, tz="UTC")]
    e = rasgos_equipo(partidos, datos.contexto)
    f = f.merge(e, on=["match_id", "side"], how="outer")
    h = f[f["side"] == "home"].set_index("match_id").add_prefix("h_")
    v = f[f["side"] == "away"].set_index("match_id").add_prefix("a_")
    z = base.join(h, on="match_id").join(v, on="match_id")
    z = z.reset_index(drop=True)
    print(f"partidos con A0 y once: {len(z)}")
    # observaciones: gol local con rasgos propios y del rival, gol visitante igual
    def obs(z):
        loc = pd.DataFrame({"y": z["home_goals"], "off": np.log(z["lam"]), "x_atk": z["h_x_atk"], "rot": z["h_rotacion"],
                            "aus": z["h_ausentes"], "aus_rival": z["a_ausentes"],
                            "fin": z["h_fin"], "gk_rival": z["a_gk"], "nuevo": z["h_nuevo"], "nuevo_rival": z["a_nuevo"]})
        vis = pd.DataFrame({"y": z["away_goals"], "off": np.log(z["mu"]), "x_atk": z["a_x_atk"], "rot": z["a_rotacion"],
                            "aus": z["a_ausentes"], "aus_rival": z["h_ausentes"],
                            "fin": z["a_fin"], "gk_rival": z["h_gk"], "nuevo": z["a_nuevo"], "nuevo_rival": z["h_nuevo"]})
        return pd.concat([loc, vis], ignore_index=True)

    COLS = {"A4 fuerza del once": ["x_atk"], "A5 rotación": ["rot"], "A6 habituales ausentes": ["aus", "aus_rival"],
            "A4+A5+A6": ["x_atk", "rot", "aus", "aus_rival"],
            "A3 definición y portero": ["fin", "gk_rival"], "A7 entrenador nuevo": ["nuevo", "nuevo_rival"]}
    y1x2 = np.where(z["home_goals"] > z["away_goals"], 0, np.where(z["home_goals"] == z["away_goals"], 1, 2))
    semana = z["kickoff_utc"].dt.strftime("%G-%V").to_numpy()

    def logloss(lam, mu, rho, y):
        p = probs_1x2(np.asarray(lam), np.asarray(mu), float(rho))
        return -np.log(np.clip(p[np.arange(len(y)), y], 1e-12, 1))

    base_ll = logloss(z["lam"], z["mu"], z["rho"].iloc[0], y1x2)
    cortes = pd.date_range(DESDE, z["kickoff_utc"].max() + pd.Timedelta(days=28), freq="28D", tz="UTC")
    print(f"\nA0 solo: log-loss 1X2 {base_ll[z['kickoff_utc'] >= DESDE].mean():.4f} en {int((z['kickoff_utc'] >= DESDE).sum())} partidos (desde 2025-01)")
    for nombre, cols in COLS.items():
        ll = np.full(len(z), np.nan)
        for c0, c1 in zip(cortes[:-1], cortes[1:]):
            ent, pru = z[z["kickoff_utc"] < c0], z[(z["kickoff_utc"] >= c0) & (z["kickoff_utc"] < c1)]
            if pru.empty:
                continue
            o = obs(ent).dropna(subset=cols)
            if len(o) < 1600:
                continue
            b, _ = poisson_offset(o[cols].to_numpy(float), o["y"].to_numpy(float), o["off"].to_numpy(float))
            ops = obs(pru)
            n = len(pru)
            ok_m = (ops[cols].notna().all(axis=1).to_numpy()[:n] & ops[cols].notna().all(axis=1).to_numpy()[n:])
            if not ok_m.any():
                continue
            mu_ = np.exp(ops["off"].to_numpy() + b[0] + np.nan_to_num(ops[cols].to_numpy(float)) @ b[1:])
            idx = pru.index.to_numpy()[ok_m]
            ll[idx] = logloss(mu_[:n][ok_m], mu_[n:][ok_m], z["rho"].iloc[0], y1x2[idx])
        ok = ~np.isnan(ll)
        dm = diebold_mariano(ll[ok], base_ll[ok], semana[ok])
        o = obs(z[z["kickoff_utc"] < cortes[-2]]).dropna(subset=cols)
        b, se = poisson_offset(o[cols].to_numpy(float), o["y"].to_numpy(float), o["off"].to_numpy(float))
        coef = ", ".join(f"{c} {bb:+.4f} (t {bb / s_:+.1f})" for c, bb, s_ in zip(cols, b[1:], se[1:]))
        print(f"{nombre:26s} n {ok.sum():5d}  Δlog-loss {dm['delta']:+.5f} (t {dm['t']:+.2f})  coeficientes: {coef}")


if __name__ == "__main__":
    main()
