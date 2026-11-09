import numpy as np
import pandas as pd

from qf.eval import backtest_ligas_nuevas as b


def _oos(n=600, informativo=True, seed=3, liga="gb.championship"):
    """Resultados 1X2 sorteados desde p verdaderas; el modelo informativo las conoce, el plano no."""
    rng = np.random.default_rng(seed)
    fuerza = rng.normal(0, 0.8, n)
    p = np.exp(np.c_[fuerza * 0.6 + 0.2, np.zeros(n) + 0.0, -fuerza * 0.6])
    p = p / p.sum(axis=1, keepdims=True)
    y = np.array([rng.choice(3, p=r) for r in p])
    q = p if informativo else np.tile(np.bincount(y, minlength=3) / n, (n, 1))
    k = pd.date_range("2025-07-05", periods=n, freq="8h", tz="UTC")
    return pd.DataFrame({"match_id": np.arange(n), "league_id": liga, "kickoff_utc": k, "outcome": y,
                         "p_home": q[:, 0], "p_draw": q[:, 1], "p_away": q[:, 2], "both_known": True,
                         "mk_home": np.nan, "mk_draw": np.nan, "mk_away": np.nan})


def test_un_modelo_informativo_pasa_c1_c2_c3_y_uno_plano_no_pasa_c2():
    base = np.array([0.45, 0.27, 0.28])
    bueno = b.evaluar_liga(_oos(), base)
    assert bueno["c1"] and bueno["c2"] and bueno["c3"]
    plano = b.evaluar_liga(_oos(informativo=False), base)
    assert plano["c1"] and not plano["c2"]


def test_pocos_partidos_no_pasan_c1_y_sin_base_no_pasa_c2():
    assert not b.evaluar_liga(_oos(n=80), np.array([0.4, 0.3, 0.3]))["c1"]
    assert not b.evaluar_liga(_oos(), np.array([np.nan] * 3))["c2"]


def test_un_modelo_sobreconfiado_falla_la_calibracion():
    o = _oos()
    p = o[["p_home", "p_draw", "p_away"]].to_numpy()
    sobre = p ** 3 / (p ** 3).sum(axis=1, keepdims=True)
    o[["p_home", "p_draw", "p_away"]] = sobre
    assert not b.evaluar_liga(o, np.array([0.45, 0.27, 0.28]))["c3"]


def test_regresion_detecta_la_liga_que_empeora_y_no_la_que_igual():
    a = _oos(liga="es.laliga", seed=5)
    control_igual = a.copy()
    r = b.regresion(a, control_igual, ["es.laliga"])
    assert r["es.laliga"]["delta"] == 0 and not r["es.laliga"]["peor"]
    peor = a.copy()
    peor[["p_home", "p_draw", "p_away"]] = 1 / 3  # el modelo con las ligas nuevas queda plano
    r = b.regresion(peor, a, ["es.laliga"])
    assert r["es.laliga"]["delta"] > b.CRITERIOS["regresion_max"] and r["es.laliga"]["peor"]


def test_frecuencia_previa_solo_usa_partidos_anteriores_al_tramo():
    k = pd.date_range("2024-01-01", periods=200, freq="2D", tz="UTC")
    h = pd.DataFrame({"league_id": "x", "kickoff_utc": k, "home_goals": 1, "away_goals": 0})
    f = b.frecuencia_previa(h, "x", pd.Timestamp("2024-06-01", tz="UTC"))
    assert np.isnan(f).all()  # solo ~76 partidos antes: no se inventa una base
    f = b.frecuencia_previa(h, "x", pd.Timestamp("2025-07-01", tz="UTC"))
    assert f.tolist() == [1.0, 0.0, 0.0]
