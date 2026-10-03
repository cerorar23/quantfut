from datetime import datetime, timezone

import numpy as np
import pandas as pd

from qf.eval import early_vs_close as evc


def _partidos(n: int, hacia_modelo: float, seed: int = 0) -> pd.DataFrame:
    """El cierre recorre `hacia_modelo` del camino entre la temprana y el modelo."""
    rng = np.random.default_rng(seed)
    pe = rng.dirichlet([6, 3, 4], size=n)
    pm = rng.dirichlet([1, 1, 1], size=n) * 0.15 + pe * 0.85
    pc = (1 - hacia_modelo) * pe + hacia_modelo * pm
    pc = pc + rng.normal(0, 0.004, pc.shape)
    pc = np.clip(pc, 0.01, None)
    pc = pc / pc.sum(axis=1, keepdims=True)
    d = pd.DataFrame({
        "kickoff_utc": pd.date_range("2020-01-01", periods=n, freq="6h", tz="UTC"),
        "league_id": np.array(["a", "b", "c", "d", "e"])[np.arange(n) % 5],
        "p_home": pm[:, 0], "p_draw": pm[:, 1], "p_away": pm[:, 2],
        "outcome": rng.integers(0, 3, n),
    })
    d["week"] = d["kickoff_utc"].dt.tz_localize(None).dt.to_period("W").astype(str)
    for j, s in enumerate(evc.SEL):
        d[f"pe_{s}"], d[f"pc_{s}"] = pe[:, j], pc[:, j]
        d[f"price_early_{s}"] = 1 / (pe[:, j] * 1.03)
    return d


def test_match_id_igual_que_history_fd():
    ko = datetime(2023, 8, 19, 17, 30, tzinfo=timezone.utc)
    assert (evc.match_id("es.laliga", "2324", "Almeria", "Real Madrid", ko)
            == "es.laliga:2324:almeria-realmadrid:20230819")


def test_pendiente_detecta_que_el_mercado_va_hacia_el_modelo():
    mov = evc.movimiento(_partidos(2000, 0.5), iterations=200)
    assert 0.4 < mov["pendiente"] < 0.6
    assert mov["ic95"][0] > 0


def test_sin_informacion_la_pendiente_incluye_el_cero():
    mov = evc.movimiento(_partidos(2000, 0.0), iterations=200)
    assert mov["ic95"][0] <= 0 <= mov["ic95"][1]
    assert evc.veredicto(mov, {"ev_cierre_ic95": [1.0, 2.0]}) == "SIN SEÑAL"


def test_la_seleccion_no_lee_cierre_ni_resultado():
    d = _partidos(500, 0.5)
    a = evc.seleccionar(d)
    alterado = d.copy()
    for s in evc.SEL:
        alterado[f"pc_{s}"] = 1 / 3
    alterado["outcome"] = 0
    b = evc.seleccionar(alterado)
    assert len(a) > 0
    assert a["sel"].tolist() == b["sel"].tolist()
    assert a["kickoff_utc"].tolist() == b["kickoff_utc"].tolist()


def test_ligas_params_solo_con_el_pasado():
    corte = pd.Timestamp("2020-01-01", tz="UTC")
    df = pd.DataFrame({
        "kickoff_utc": pd.to_datetime(["2019-06-01", "2020-06-01"], utc=True),
        "league_id": ["x", "x"], "home_goals": [1, 9], "away_goals": [1, 1],
    })
    m = evc._KalmanSinFuturo(corte)
    m._estimate_league_params(df)
    assert m.leagues["x"].home_adv == 0.0
