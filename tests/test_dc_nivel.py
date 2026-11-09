import math
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from qf.model.dixon_coles import DixonColes

CORTE = datetime(2026, 11, 1, tzinfo=timezone.utc)


def _liga(liga, rng, factor_reciente=1.0, dias=900, recientes=100, equipos=10, base=1.35):
    """Calendario sintético: cada día un partido por pareja al azar; los goles suben `factor_reciente` en los últimos días."""
    t = [f"{liga}{i}" for i in range(equipos)]
    fuerza = {x: rng.normal(0, 0.15) for x in t}
    filas = []
    for d in range(dias):
        h, a = rng.choice(equipos, 2, replace=False)
        f = factor_reciente if d >= dias - recientes else 1.0
        lam = base * f * math.exp(0.25 + fuerza[t[h]] - fuerza[t[a]])
        mu = base * f * math.exp(fuerza[t[a]] - fuerza[t[h]])
        filas.append({"kickoff_utc": CORTE - timedelta(days=dias - d + 1), "home_team": t[h], "away_team": t[a],
                      "home_goals": rng.poisson(lam), "away_goals": rng.poisson(mu), "home_xg": np.nan,
                      "away_xg": np.nan, "league_id": liga})
    return pd.DataFrame(filas)


def _datos(factor_a, seed=3):
    rng = np.random.default_rng(seed)
    return pd.concat([_liga("a.liga", rng, factor_a), _liga("b.liga", rng, 1.0)], ignore_index=True)


def _base(df, **kw):
    m = DixonColes(halflife_days=270.0, xg_blend=0.0, **kw).fit(df, as_of=CORTE)
    return dict(zip(m.params.leagues, m.params.base))


def test_apagado_por_defecto_no_cambia_nada():
    df = _datos(1.0)
    a = _base(df)
    b = _base(df, nivel_halflife_days=0.0)
    assert a == b


def test_sube_el_nivel_de_la_liga_que_acelera_y_no_toca_la_estable():
    df = _datos(1.30)
    sin, con = _base(df), _base(df, nivel_halflife_days=45.0, nivel_prior_goles=20.0)
    assert con["a.liga"] - sin["a.liga"] > math.log(1.04)       # la liga con +30 % reciente sube
    assert abs(con["b.liga"] - sin["b.liga"]) < 0.04             # la estable queda prácticamente igual


def test_baja_el_nivel_si_los_goles_caen():
    df = _datos(0.75)
    sin, con = _base(df), _base(df, nivel_halflife_days=45.0, nivel_prior_goles=20.0)
    assert con["a.liga"] - sin["a.liga"] < -math.log(1.04)


def test_el_factor_tiene_tope():
    df = _datos(3.0)
    sin, con = _base(df), _base(df, nivel_halflife_days=20.0, nivel_prior_goles=1.0)
    assert con["a.liga"] - sin["a.liga"] <= math.log(DixonColes.NIVEL_R_MAX) + 1e-9


def test_un_prior_grande_frena_la_correccion():
    df = _datos(1.30)
    sin = _base(df)
    suave = _base(df, nivel_halflife_days=45.0, nivel_prior_goles=2000.0)
    fuerte = _base(df, nivel_halflife_days=45.0, nivel_prior_goles=5.0)
    assert 0 < suave["a.liga"] - sin["a.liga"] < fuerte["a.liga"] - sin["a.liga"]


def test_es_point_in_time_un_partido_posterior_al_corte_no_mueve_nada():
    df = _datos(1.30)
    futuro = df.iloc[[0]].assign(kickoff_utc=CORTE + timedelta(days=3), home_goals=9, away_goals=9)
    a = _base(df, nivel_halflife_days=45.0)
    # el cargador de entrenamiento solo trae partidos anteriores al corte: aquí se filtra igual que hace el backtest
    b = _base(pd.concat([df, futuro])[lambda x: x["kickoff_utc"] < CORTE], nivel_halflife_days=45.0)
    assert a == b
