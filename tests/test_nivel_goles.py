import numpy as np
import pandas as pd

from qf.eval import nivel_goles as n
from qf.model.calibration import probs_1x2


def _oos(factor, seed=4, filas=1500):
    """OOS sintético: goles reales con media 3,0; el modelo predice `factor` veces esa media."""
    rng = np.random.default_rng(seed)
    lam_v, mu_v = 1.65, 1.35
    hg, ag = rng.poisson(lam_v, filas), rng.poisson(mu_v, filas)
    lam, mu = np.full(filas, lam_v * factor), np.full(filas, mu_v * factor)
    p = probs_1x2(lam, mu, -0.03)
    k = pd.date_range("2025-07-05", periods=filas, freq="8h", tz="UTC")
    return pd.DataFrame({"match_id": np.arange(filas), "kickoff_utc": k, "league_id": np.where(np.arange(filas) % 2, "a", "b"),
                         "outcome": np.where(hg > ag, 0, np.where(hg == ag, 1, 2)), "home_goals": hg, "away_goals": ag,
                         "p_home": p[:, 0], "p_draw": p[:, 1], "p_away": p[:, 2], "lam": lam, "mu": mu, "rho": -0.03,
                         "both_known": True})


def test_identicos_no_dan_diferencias():
    d = _oos(0.9)
    r = n.comparar(d, d.copy())
    assert r["n2"]["delta_agrupado"] == 0 and r["n3"]["delta_medio"] == 0 and r["n1"]["total_antes"] == r["n1"]["total_despues"]


def test_corregir_el_nivel_acerca_el_sesgo_y_mejora_los_mercados_de_goles():
    sin, con = _oos(0.88), _oos(1.0)
    r = n.comparar(sin, con)
    assert r["n1"]["total_antes"] < -0.25 and abs(r["n1"]["total_despues"]) < 0.05
    assert r["n3"]["delta_medio"] < 0 and r["n3"]["ok"] and r["n1"]["ok"]


def test_sobrecorregir_se_detecta():
    sin, con = _oos(1.0), _oos(1.25)
    r = n.comparar(sin, con)
    assert not r["n1"]["ok"] and r["n3"]["delta_medio"] > 0 and not r["n3"]["ok"]


def _serie_con_deriva(meses=22, por_mes=150, seed=11):
    """OOS sintético de 2 ligas: el modelo predice 3,0 goles, los reales suben de 3,0 a 3,4 en el último tercio."""
    rng = np.random.default_rng(seed)
    filas = []
    for m in range(meses):
        real = 3.0 if m < meses * 2 // 3 else 3.4
        for i in range(por_mes):
            hg, ag = rng.poisson(real * 0.55), rng.poisson(real * 0.45)
            filas.append({"match_id": len(filas), "kickoff_utc": pd.Timestamp("2024-07-05", tz="UTC") + pd.Timedelta(days=30 * m + i % 28),
                          "league_id": "a" if i % 2 else "b", "outcome": 0 if hg > ag else 1 if hg == ag else 2, "home_goals": hg,
                          "away_goals": ag, "lam": 1.65, "mu": 1.35, "rho": -0.03, "both_known": True,
                          "p_home": 0.0, "p_draw": 0.0, "p_away": 0.0})
    d = pd.DataFrame(filas)
    p = probs_1x2(d["lam"].to_numpy(), d["mu"].to_numpy(), -0.03)
    d[["p_home", "p_draw", "p_away"]] = p
    return d


def test_corregir_oos_sigue_la_deriva_y_no_mira_el_futuro():
    d = _serie_con_deriva()
    c = n.corregir_oos(d, desde="2025-07-01")
    c = c.assign(_k=pd.to_datetime(c["kickoff_utc"], utc=True))
    # tras la deriva (último tramo) el esperado sube hacia 3,4; antes de ella se queda cerca de 3,0
    tarde = c[c["_k"] >= pd.Timestamp("2026-03-01", tz="UTC")]
    pronto = c[c["_k"] < pd.Timestamp("2025-10-01", tz="UTC")]
    assert (tarde["lam"] + tarde["mu"]).mean() > 3.15 and abs((pronto["lam"] + pronto["mu"]).mean() - 3.0) < 0.08
    # no mira el futuro: cambiar los goles de un mes posterior no mueve las lambdas de un mes anterior
    d2 = d.copy()
    d2.loc[pd.to_datetime(d2["kickoff_utc"], utc=True) >= pd.Timestamp("2026-03-01", tz="UTC"), ["home_goals", "away_goals"]] = 9
    c2 = n.corregir_oos(d2, desde="2025-07-01")
    antes = lambda x: x[pd.to_datetime(x["kickoff_utc"], utc=True) < pd.Timestamp("2026-03-01", tz="UTC")][["match_id", "lam", "mu"]]
    pd.testing.assert_frame_equal(antes(c).reset_index(drop=True), antes(c2).reset_index(drop=True))


def test_corregir_oos_mejora_el_sesgo_y_pasa_la_comparacion():
    d = _serie_con_deriva()
    base = d[pd.to_datetime(d["kickoff_utc"], utc=True) >= pd.Timestamp("2025-07-01", tz="UTC")]
    c = n.corregir_oos(d, desde="2025-07-01")
    r = n.comparar(base, c)
    assert abs(r["n1"]["total_despues"]) < abs(r["n1"]["total_antes"]) and r["n3"]["delta_medio"] < 0
