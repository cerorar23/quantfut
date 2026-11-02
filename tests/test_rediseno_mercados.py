"""Probabilidades y liquidación de los mercados pedidos por el titular (líneas asiáticas con devolución incluidas)."""
import numpy as np
import pytest

from qf.eval.rediseno_mercados import adelgazar, liquidar, matrices_mitades, prob_linea


def test_linea_entera_devuelve_y_media_no():
    soporte = np.arange(6); pmf = np.array([[0.1, 0.2, 0.3, 0.2, 0.1, 0.1]])
    g, d = prob_linea(pmf, soporte, 2.0, "menos")
    assert g[0] == pytest.approx(0.3) and d[0] == pytest.approx(0.3)  # 0 o 1 gana, 2 devuelve
    g, d = prob_linea(pmf, soporte, 2.5, "mas")
    assert g[0] == pytest.approx(0.4) and d[0] == 0
    assert liquidar(np.array([2, 1, 3]), 2.0, "menos").tolist() == ["devuelve", "gana", "pierde"]


def test_mitades_suman_el_total_y_adelgazado():
    m1, m2 = matrices_mitades(np.array([1.5]), np.array([1.0]), 0.45)
    assert m1.sum() == pytest.approx(1, abs=1e-6) and m2.sum() == pytest.approx(1, abs=1e-6)
    # goles esperados de la primera parte = 45 % del total
    g = np.arange(m1.shape[1])
    assert (m1[0].sum(1) * g).sum() == pytest.approx(0.675, abs=1e-3)
    # adelgazar una Poisson(4) con s = 0,35 da Poisson(1,4)
    from scipy.stats import poisson
    p = poisson.pmf(np.arange(30), 4.0)[None, :]
    q = adelgazar(p, 0.35)
    assert q[0, :5] == pytest.approx(poisson.pmf(np.arange(5), 1.4), abs=1e-6)


def test_props_solo_usan_partidos_anteriores_y_bn():
    import pandas as pd
    from qf.eval.rediseno_jugadores import kappa_nb, p_mas, previos
    n = 30
    j = pd.DataFrame({"jugador_id": [7] * n, "posicion": ["F"] * n, "titular": [True] * n, "minutos": [90.0] * n,
                      "kickoff_utc": pd.date_range("2024-01-01", periods=n, freq="7D", tz="UTC"),
                      "tiros_puerta": [2.0] * (n - 1) + [10.0], "tiros_totales": [3.0] * n, "pases_acertados": [40.0] * n,
                      "faltas_recibidas": [1.0] * n, "goles": [0.0] * n, "xg": [np.nan] * n, "tarjeta": [0.0] * n})
    out = previos(j, "2024-03-01")
    assert out["m_tiros_puerta"].iloc[-1] == pytest.approx(out["m_tiros_puerta"].iloc[-2], rel=0.05)  # el 10 no entra
    rng = np.random.default_rng(1)
    m = np.full(20000, 50.0); y = rng.negative_binomial(20, 20 / 70, 20000)
    assert kappa_nb(y.astype(float), m) == pytest.approx(20, rel=0.15)
    assert p_mas(np.array([1.0]), 0.5)[0] == pytest.approx(1 - np.exp(-1))


def test_platt_corrige_una_probabilidad_inflada():
    from qf.eval.rediseno_jugadores import platt
    rng = np.random.default_rng(3)
    verdad = rng.uniform(0.05, 0.6, 20000)
    y = (rng.uniform(size=verdad.size) < verdad).astype(float)
    inflada = np.clip(verdad * 1.3, 0, 0.99)
    f = platt(inflada, y)
    assert f(inflada).mean() == pytest.approx(y.mean(), abs=0.01)


def test_cuotas_reales_handicap_y_liquidacion():
    """PropLine: la línea del hándicap es la del equipo elegido (local −1,0 gana si gana por 2 o más)."""
    import importlib.util
    from pathlib import Path
    ruta = Path(__file__).resolve().parents[1] / "scripts" / "rediseno_futbol" / "cuotas_reales.py"
    spec = importlib.util.spec_from_file_location("cuotas_reales", ruta)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    r = {"home_goals": 2, "away_goals": 1}
    assert m.resultado("spreads", "home", -1.0, r) == "devuelve"
    assert m.resultado("spreads", "away", 1.5, r) == "gana"
    assert m.resultado("double_chance", "X2", -999, r) == "pierde"
    M = np.zeros((3, 3)); M[2, 1] = 1.0  # 2-1 seguro
    assert m.probs_motor("spreads", "home", -1.0, M, None, None, None, None) == pytest.approx((0.0, 1.0))
    assert m.probs_motor("spreads", "away", 1.5, M, None, None, None, None)[0] == pytest.approx(1.0)


def test_sin_margen_empareja_handicap_local_con_visitante_opuesto():
    import importlib.util
    import pandas as pd
    from pathlib import Path
    ruta = Path(__file__).resolve().parents[1] / "scripts" / "rediseno_futbol" / "cuotas_reales.py"
    spec = importlib.util.spec_from_file_location("cuotas_reales", ruta)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    c = pd.DataFrame({"match_id": 1, "bookmaker": "pinnacle", "market": "spreads",
                      "selection": ["home", "away", "home", "away"], "line": [-0.5, 0.5, 0.5, -0.5],
                      "price": [2.72, 1.50, 1.56, 2.55]})
    q = m.sin_margen(c).set_index(["seleccion", "linea"])["q"]
    assert q[("home", -0.5)] + q[("away", 0.5)] == pytest.approx(1)
    assert q[("home", -0.5)] == pytest.approx((1 / 2.72) / (1 / 2.72 + 1 / 1.50))
    h2h = pd.DataFrame({"match_id": 2, "bookmaker": "x", "market": "h2h", "selection": ["home", "draw", "away"],
                        "line": np.nan, "price": [2.0, 3.5, 4.0]})
    d = m.sin_margen(h2h).set_index(["mercado", "seleccion"])["q"]
    assert d[("double_chance", "1X")] == pytest.approx(d[("h2h", "home")] + d[("h2h", "draw")])
