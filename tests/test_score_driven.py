"""A0 del rediseño: fuerzas de ataque y defensa actualizadas partido a partido (Koopman-Lit, score-driven)."""
import numpy as np
import pandas as pd

from qf.model.score_driven import ScoreDriven


def liga_simulada(n_temporadas=6, seed=0):
    """10 equipos con fuerza fija; el equipo 0 es claramente el mejor."""
    rng = np.random.default_rng(seed)
    ataque = np.linspace(0.5, -0.4, 10); defensa = np.linspace(0.4, -0.4, 10)
    filas, t = [], pd.Timestamp("2015-08-01", tz="UTC")
    for _ in range(n_temporadas):
        for h in range(10):
            for a in range(10):
                if h == a:
                    continue
                lam = np.exp(0.15 + 0.25 + ataque[h] - defensa[a]); mu = np.exp(0.15 + ataque[a] - defensa[h])
                hg, ag = rng.poisson(lam), rng.poisson(mu)
                filas.append({"match_id": f"m{len(filas)}", "kickoff_utc": t, "league_id": "x", "home_team": str(h),
                              "away_team": str(a), "home_goals": hg, "away_goals": ag, "home_xg": np.nan,
                              "away_xg": np.nan, "outcome": 0 if hg > ag else 1 if hg == ag else 2})
                t += pd.Timedelta(hours=8)
    return pd.DataFrame(filas)


def test_aprende_quien_es_mejor_y_no_mira_el_futuro():
    df = liga_simulada()
    corte = df["kickoff_utc"].iloc[300]
    m = ScoreDriven(fin_estimacion=corte)
    m.ajustar(df[df["kickoff_utc"] < corte], corte)
    estado = dict(m.ataque)
    pred = m.predecir(pd.DataFrame({"home_team": ["0", "9"], "away_team": ["9", "0"], "league_id": ["x", "x"]}))
    assert pred.loc[0, "lam"] > pred.loc[1, "lam"] and pred.loc[0, "mu"] < pred.loc[1, "mu"]
    assert m.ataque == estado  # predecir no actualiza nada
    # con más historia, el estado avanza solo con los partidos nuevos (incremental) y los hiperparámetros no cambian
    hip = m.hip.copy()
    corte2 = df["kickoff_utc"].iloc[500]
    m.ajustar(df[df["kickoff_utc"] < corte2], corte2)
    assert np.allclose(m.hip, hip) and m.visto == 500
    assert m.ataque["0"] > m.ataque["9"] and m.defensa["0"] > m.defensa["9"]


def test_la_verosimilitud_mejora_a_la_estatica_sin_pasos():
    df = liga_simulada()
    m = ScoreDriven(fin_estimacion=df["kickoff_utc"].iloc[-1])
    nll_cero = m.nll(np.array([0.0, 0.0, 0.0, 0.0, -0.05]), df)
    m.ajustar(df, df["kickoff_utc"].iloc[-1] + pd.Timedelta(days=1))
    assert m.nll(m.hip, df) < nll_cero
