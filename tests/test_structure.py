import numpy as np
import pandas as pd
import pytest

from qf.model import structure as st
from qf.model.pricing import score_matrix

LAM = np.array([0.3, 1.1, 1.6, 2.4, 3.8])
MU = np.array([0.5, 0.9, 1.2, 0.7, 2.9])


def _means(m):
    k = np.arange(st.G + 1)
    return m.sum(axis=2) @ k, m.sum(axis=1) @ k


def test_casos_limite_reproducen_poisson():
    base = st.poisson_matrix(LAM, MU)
    assert np.allclose(st.weibull_copula_matrix(LAM, MU, 1.0, 0.0), base, atol=1e-9)
    assert np.allclose(st.cmp_matrix(LAM, MU, 1.0), base, atol=1e-9)
    assert np.allclose(st.bivariate_poisson_matrix(LAM, MU, 0.0), base, atol=1e-12)
    assert np.allclose(st.dc_tau_matrix(LAM, MU, 0.0), base, atol=1e-12)


def test_tau_coincide_con_el_de_produccion():
    ours = st.dc_tau_matrix(LAM[:1], MU[:1], -0.08)[0]
    prod = score_matrix(LAM[0], MU[0], -0.08, max_goals=st.G)
    assert np.allclose(ours, prod / prod.sum(), atol=1e-12)


@pytest.mark.parametrize("build", [
    lambda: st.bivariate_poisson_matrix(LAM, MU, 0.2),
    lambda: st.cmp_matrix(LAM, MU, 0.7),
    lambda: st.cmp_matrix(LAM, MU, 1.6),
    lambda: st.weibull_copula_matrix(LAM, MU, 0.9, 0.0),
    lambda: st.weibull_copula_matrix(LAM, MU, 1.3, 0.0),
])
def test_las_medias_de_dixon_coles_se_conservan(build):
    home, away = _means(build())
    # Las 4 primeras filas (medias <= 2,4): ahí el truncado a 10 goles, común a
    # todos los brazos, es despreciable y lo que queda es el igualado de medias.
    assert np.allclose(home[:4], LAM[:4], atol=3e-3)
    assert np.allclose(away[:4], MU[:4], atol=3e-3)


def test_weibull_es_distribucion_valida_en_todo_el_rango():
    for c in (0.85, 1.0, 1.4):
        p = st.weibull_marginal(np.array([0.05, 1.0, 2.0, 3.0]), c)
        assert (p >= 0).all() and np.allclose(p.sum(axis=1), 1.0, atol=2e-3)


def test_la_dispersion_va_en_el_sentido_que_dice_el_parametro():
    k = np.arange(st.G + 1)
    var = lambda p: p @ k**2 - (p @ k) ** 2  # noqa: E731
    mean = np.array([1.5])
    assert var(st.cmp_marginal(mean, 0.6)[0]) > 1.5 > var(st.cmp_marginal(mean, 1.8)[0])
    assert (var(st.weibull_marginal(mean, 0.9)[0]) > 1.5
            > var(st.weibull_marginal(mean, 1.3)[0]))


def test_frank_conserva_marginales_y_crea_dependencia():
    p, q = st._poisson_pmf(LAM), st._poisson_pmf(MU)
    m = st.copula_matrix(p, q, 3.0)
    assert np.allclose(m.sum(axis=2), p / p.sum(axis=1, keepdims=True), atol=2e-3)
    k = np.arange(st.G + 1)
    cov = np.einsum("nij,i,j->n", m, k, k) - (m.sum(axis=2) @ k) * (m.sum(axis=1) @ k)
    assert (cov > 0).all()


def test_probit_suma_uno_y_responde_al_indice():
    params = [1.0, 0.5, -1.5, 0.0, -0.5, 0.0, 0.0, -0.5]
    p = st.probit_gd_probs(np.array([0.8, 2.0]), np.array([2.0, 0.8]), params, 1.0)
    assert np.allclose(p.sum(axis=1), 1.0)
    x12 = st.x12_from_gd(p)
    assert x12[1, 0] > x12[0, 0]


def _synthetic(n=1600, lam3=0.25, seed=7):
    rng = np.random.default_rng(seed)
    lam = rng.uniform(0.8, 2.2, n)
    mu = rng.uniform(0.6, 1.8, n)
    x3 = rng.poisson(lam3, n)
    hg = rng.poisson(lam - lam3) + x3
    ag = rng.poisson(mu - lam3) + x3
    kick = pd.Timestamp("2025-01-01", tz="UTC") + pd.to_timedelta(
        np.sort(rng.uniform(0, 360, n)), unit="D")
    return pd.DataFrame({"kickoff_utc": kick, "lam": lam, "mu": mu,
                         "home_goals": hg, "away_goals": ag})


def test_recupera_la_dependencia_verdadera_y_lo_detecta():
    out = st.evaluate(_synthetic(), min_fit_rows=300)
    assert out["ok"]
    assert out["brazos"]["bivariate_poisson"]["params_ultimo_mes"]["theta"] == \
        pytest.approx(0.25, abs=0.08)
    assert out["contra_titular"]["bivariate_poisson"]["score_log_loss"]["estimate"] > 0


def test_todos_los_brazos_sobre_las_mismas_filas_y_sin_mirar_el_futuro(monkeypatch):
    df = _synthetic(n=900)
    seen = []
    original = st.ARMS["poisson"]["fit"]

    def spy(rows):
        seen.append(len(rows["lam"]))
        return original(rows)
    monkeypatch.setitem(st.ARMS["poisson"], "fit", spy)
    out = st.evaluate(df, min_fit_rows=300)
    month = pd.to_datetime(df["kickoff_utc"]).dt.tz_convert(None).dt.to_period("M")
    sizes = month.value_counts().sort_index()
    prior = sizes.cumsum().shift(1, fill_value=0)
    fitted = prior >= 300
    # Cada ajuste usa exactamente las filas de los meses anteriores.
    assert seen == [int(v) for v in prior[fitted]]
    assert out["n_obs"] == int(sizes[fitted].sum())
    assert set(out["contra_titular"]) == set(st.ARMS) - {st.BASELINE}
