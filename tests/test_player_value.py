"""
Comparación de brazos del XI (fuerza por jugador, Fase B1).

Lo que fijan: los tres brazos se ajustan y validan sobre las MISMAS filas, y
"XI con valor" solo queda validado si además gana al XI simple.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from qf.model.lineup_challenger import LINEUP_FEATURES
from qf.model.player_ratings import NOTA_FEATURES, VALOR_FEATURES


def _frame(senal_valor: float, n: int = 1000):
    rng = np.random.default_rng(1)
    d = pd.DataFrame({
        "match_id": [f"m{i}" for i in range(n)], "league_id": ["A", "B"] * (n // 2),
        "kickoff_utc": pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC"),
        "base_lam": 1.4, "base_mu": 1.1, "rho": -0.05})
    for c in LINEUP_FEATURES + VALOR_FEATURES + NOTA_FEATURES:
        d[c] = rng.normal(size=n)
    d["home_goals"] = rng.poisson(1.4 * np.exp(senal_valor * d["home_d_tiros"]))
    d["away_goals"] = rng.poisson(1.1, n)
    return d


def _informes_fijos(monkeypatch, valor_ok, valor_rps, valor_ll):
    """
    Sustituye el ajuste por informes controlados. Con 300 filas de validación
    el ECE de dos brazos se ordena casi al azar (medido el 1-oct-2026), así
    que la lógica de `comparar` se prueba sin depender de esa lotería.
    """
    from qf.model import lineup_challenger as lc
    vistos = []

    def falso(frame, rho=0.0, features=None, **_):
        vistos.append((tuple(features), len(frame)))
        modelo = lc.LineupLambdaChallenger(lc.LineupParams(
            [0.0] * len(features), [1.0] * len(features), [0.0] * (len(features) + 1),
            [0.0] * (len(features) + 1), rho, 0.5, 700, True, list(features)))
        if features == VALOR_FEATURES:
            rep = {"ok": valor_ok, "rps_after": valor_rps, "log_loss_after": valor_ll}
        else:
            rep = {"ok": True, "rps_after": 0.210, "log_loss_after": 1.040}
        return modelo, rep

    monkeypatch.setattr(lc, "fit_and_validate", falso)
    return vistos


def test_el_valor_que_gana_al_simple_queda_validado(monkeypatch):
    from qf.model.player_value import comparar
    vistos = _informes_fijos(monkeypatch, True, 0.205, 1.030)
    informe, modelos = comparar(_frame(0.4), rho=-0.05)
    assert informe["n_filas"] == 1000
    assert {n for _, n in vistos} == {1000}, "los tres brazos, mismas filas"
    assert informe["valor"]["gana_al_simple"] is True
    assert modelos["valor"].params.offline_validated is True
    assert modelos["nota"].params.offline_validated is False


def test_el_valor_que_no_gana_al_simple_no_se_valida(monkeypatch):
    from qf.model.player_value import comparar
    _informes_fijos(monkeypatch, True, 0.211, 1.030)
    informe, modelos = comparar(_frame(0.4), rho=-0.05)
    assert informe["valor"]["gana_al_simple"] is False
    assert modelos["valor"].params.offline_validated is False


def test_sin_senal_no_se_valida():
    from qf.model.player_value import comparar
    informe, modelos = comparar(_frame(0.0), rho=-0.05)
    assert informe["valor"]["gana_al_simple"] is False or not informe["valor"]["ok"]
    assert modelos["valor"] is None or modelos["valor"].params.offline_validated is False


def test_filas_incompletas_quedan_fuera_de_los_tres():
    from qf.model.player_value import comparar
    d = _frame(0.4)
    d.loc[:9, "home_d_tiros"] = np.nan
    informe, _ = comparar(d, rho=-0.05)
    assert informe["n_filas"] == 990
