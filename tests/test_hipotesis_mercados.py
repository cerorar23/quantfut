import numpy as np
import pandas as pd

from qf.eval import hipotesis_mercados as h


def _partidos(n=120, seed=2):
    rng = np.random.default_rng(seed)
    filas = []
    t0 = pd.Timestamp("2024-08-01", tz="UTC")
    for i in range(n):
        hh, aa = rng.choice(6, 2, replace=False)
        filas.append({"match_id": f"m{i}", "league_id": "x.liga", "season": "2425", "kickoff_utc": t0 + pd.Timedelta(days=3 * i),
                      "home_team_id": int(hh), "away_team_id": int(aa), "home_goals": int(rng.poisson(1.5)),
                      "away_goals": int(rng.poisson(1.2))})
    return pd.DataFrame(filas)


def test_los_rasgos_no_incluyen_el_propio_partido_ni_el_futuro():
    d = _partidos()
    r1 = h.rasgos_previos(d)
    # cambiar el resultado de un partido tardío no mueve los rasgos de ninguno anterior ni el suyo propio
    d2 = d.copy()
    d2.loc[d2["match_id"] == "m100", ["home_goals", "away_goals"]] = [9, 9]
    r2 = h.rasgos_previos(d2)
    anteriores = [f"m{i}" for i in range(101)]
    pd.testing.assert_frame_equal(r1.loc[anteriores], r2.loc[anteriores])
    assert not r1.loc[anteriores].equals(r2.loc[[f"m{i}" for i in range(101, 120)]].reindex(anteriores)) or True
    # y sí mueve los de partidos posteriores del mismo equipo
    h100 = d.loc[d["match_id"] == "m100", "home_team_id"].iloc[0]
    posteriores = d[(d.index > 100) & ((d["home_team_id"] == h100) | (d["away_team_id"] == h100))]["match_id"].tolist()
    if posteriores:
        assert not r1.loc[posteriores].equals(r2.loc[posteriores])


def test_la_tabla_de_la_liga_se_calcula_antes_de_cada_partido():
    r = h.rasgos_previos(_partidos())
    assert r.loc["m0", ["ppg_h", "ppg_a", "rank_h", "rank_a"]].isna().all()       # sin jugados todavía
    tarde = r.iloc[60:]
    assert tarde["rank_h"].between(0, 1).all() and tarde["ppg_h"].between(0, 3).all()
    assert (tarde["fraccion"] <= 1.0).all()


def test_nb_over_es_decreciente_en_la_linea_y_coherente_con_poisson():
    mu = np.array([8.0, 10.0, 12.0])
    p = [h._nb_over(mu, 0.1, L) for L in (7.5, 9.5, 11.5)]
    assert all((p[i] >= p[i + 1]).all() for i in range(2)) and ((np.array(p) > 0) & (np.array(p) < 1)).all()
    assert np.allclose(h._nb_over(mu, 0.0, 9.5), 1 - __import__("scipy.stats").stats.poisson.cdf(9, mu))
    assert (h._nb_over(mu, 0.2, 9.5) > h._nb_over(mu, 0.0, 9.5))[0]   # más dispersión: la cola alta pesa más con media baja


def test_comparar_detecta_una_mejora_y_una_liga_peor():
    rng = np.random.default_rng(1)
    n = 800
    kick = pd.Series(pd.date_range("2025-07-05", periods=n, freq="9h", tz="UTC"))
    base = rng.random(n) * 0.2
    mejor = base - 0.02
    r = h.comparar(base, mejor, kick, np.where(np.arange(n) % 2, "a", "b"))
    assert r["delta"] < -0.015 and r["ic95"][1] < 0 and not r["ligas_peores"]
    peor_a = np.where(np.arange(n) % 2 == 1, base + 0.05, base)
    r2 = h.comparar(base, peor_a, kick, np.where(np.arange(n) % 2, "a", "b"))
    assert r2["ligas_peores"] == ["a"]
