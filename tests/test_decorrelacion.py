"""
Decorrelación con el mercado (idea 4, Hubáček y Šír 2023).

Lo que fijan: el gradiente de la pérdida del artículo es el correcto, γ > 0
aleja de verdad al modelo del mercado, y ni las apuestas ni la elección de γ
miran el cierre, el resultado o la temporada de prueba.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import check_grad

from qf.eval import decorrelacion as dc


def _partidos(n: int = 3000, seed: int = 0) -> pd.DataFrame:
    """El mercado sabe la verdad con ruido; el modelo, con otro ruido."""
    rng = np.random.default_rng(seed)
    verdad = rng.dirichlet([6, 3, 4], size=n)
    ruido = lambda: rng.normal(0, 0.25, (n, 3))  # noqa: E731
    def prob(z):
        e = np.exp(np.log(verdad) + z)
        return e / e.sum(axis=1, keepdims=True)
    pm, pe = prob(ruido()), prob(ruido())
    d = pd.DataFrame({
        "kickoff_utc": pd.date_range("2019-08-01", periods=n, freq="16h", tz="UTC"),
        "league_id": np.array(list("abcdefg"))[np.arange(n) % 7],
        "p_home": pm[:, 0], "p_draw": pm[:, 1], "p_away": pm[:, 2],
        "lam": 1.4 * pm[:, 0] / pm[:, 2], "mu": np.full(n, 1.1),
        "outcome": np.array([rng.choice(3, p=p) for p in verdad])})
    d["week"] = d["kickoff_utc"].dt.tz_localize(None).dt.to_period("W").astype(str)
    for j, s in enumerate(dc.SEL):
        d[f"pe_{s}"], d[f"pc_{s}"] = pe[:, j], verdad[:, j]
        d[f"price_early_{s}"] = 1 / (pe[:, j] * 1.03)
    return d


def test_gradiente_correcto():
    d = _partidos(300)
    m = dc.Decorrelado(0.5)
    X = dc.variables(d)
    m.mu, m.sd = X.mean(axis=0), X.std(axis=0) + 1e-9
    A = m._diseno(X)
    Y, mk = np.eye(3)[d["outcome"].to_numpy()], dc._m(d)

    def f(w):
        t = dc._softmax(A @ w.reshape(-1, 3))
        return (((t - Y) ** 2).sum() - 0.5 * ((t - mk) ** 2).sum()) / len(A) \
            + m.l2 * (w ** 2).sum()

    def g(w):
        W = w.reshape(-1, 3)
        t = dc._softmax(A @ W)
        gt = 2 * (t - Y) - 2 * 0.5 * (t - mk)
        dz = t * (gt - (gt * t).sum(axis=1, keepdims=True))
        return (A.T @ dz / len(A) + 2 * m.l2 * W).ravel()

    w0 = np.random.default_rng(1).normal(0, 0.1, A.shape[1] * 3)
    assert check_grad(f, g, w0) < 1e-5


def test_gamma_aleja_al_modelo_del_mercado():
    d = _partidos()
    X, y, mk = dc.variables(d), d["outcome"].to_numpy(), dc._m(d)
    corr = {g: np.corrcoef(dc.Decorrelado(g).fit(X, y, mk).predict(X)[:, 0], mk[:, 0])[0, 1]
            for g in (0.0, 0.8)}
    assert corr[0.8] < corr[0.0]


def test_temporada_va_de_julio_a_junio():
    ko = pd.Series(pd.to_datetime(["2021-07-01", "2022-06-30", "2019-12-01"], utc=True))
    assert dc.temporada(ko).tolist() == ["2122", "2122", "1920"]


def test_las_apuestas_no_miran_cierre_ni_resultado():
    d = _partidos(500)
    t = dc._m(d) * 1.05
    a = dc.apuestas(d, t)
    otro = d.assign(outcome=0, **{f"pc_{s}": 1 / 3 for s in dc.SEL})
    b = dc.apuestas(otro, t)
    assert len(a) == len(b) > 0
    assert a["week"].tolist() == b["week"].tolist()


def test_gamma_se_elige_sin_mirar_la_prueba():
    d = _partidos(4000)
    d = d.assign(kickoff_utc=pd.date_range("2019-08-01", periods=len(d), freq="13h", tz="UTC"))
    d["week"] = d["kickoff_utc"].dt.tz_localize(None).dt.to_period("W").astype(str)
    s = dc.temporada(d["kickoff_utc"])
    prueba = (sorted(s.unique())[2],)
    a = dc.walk_forward(d, gammas=(0.0, 0.6), prueba=prueba)
    roto = d.copy()
    roto.loc[s == prueba[0], "outcome"] = 0
    b = dc.walk_forward(roto, gammas=(0.0, 0.6), prueba=prueba)
    assert a["por_temporada"][0]["gamma_elegido"] == b["por_temporada"][0]["gamma_elegido"]
