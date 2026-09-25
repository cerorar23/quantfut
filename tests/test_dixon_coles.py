"""
Verificación del modelo por liga con datos SIMULADOS de parámetros conocidos.

La pregunta que responden estos tests no es "¿corre sin excepciones?" sino
"¿recupera los parámetros que generaron los datos?". Si simulas dos ligas con
ventajas de local distintas y el ajuste devuelve la misma para ambas, el
modelo por liga no está haciendo nada aunque el código no falle.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from qf.model.dixon_coles import DixonColes, team_key


def simulate_league(league_id: str, n_teams: int, n_rounds: int,
                    home_adv: float, base: float, start: datetime,
                    rng: np.random.Generator) -> pd.DataFrame:
    """Genera partidos Poisson con fuerzas de equipo conocidas."""
    teams = [f"{league_id}_T{i}" for i in range(n_teams)]
    attack = rng.normal(0, 0.30, n_teams)
    attack -= attack.mean()
    defence = rng.normal(0, 0.25, n_teams)
    defence -= defence.mean()

    rows = []
    day = 0
    for _ in range(n_rounds):
        for i in range(n_teams):
            for j in range(n_teams):
                if i == j:
                    continue
                lam = math.exp(base + attack[i] - defence[j] + home_adv)
                mu = math.exp(base + attack[j] - defence[i])
                rows.append({
                    "league_id": league_id,
                    "kickoff_utc": start + timedelta(days=day % 400),
                    "home_team": teams[i],
                    "away_team": teams[j],
                    "home_goals": float(rng.poisson(lam)),
                    "away_goals": float(rng.poisson(mu)),
                    "home_xg": np.nan,
                    "away_xg": np.nan,
                })
                day += 1
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def two_league_fit():
    """Dos ligas con ventaja de local y nivel de goles deliberadamente distintos."""
    rng = np.random.default_rng(7)
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    a = simulate_league("liga_alta", 10, 4, home_adv=0.45, base=0.25,
                        start=start, rng=rng)
    b = simulate_league("liga_baja", 10, 4, home_adv=0.10, base=0.00,
                        start=start, rng=rng)
    df = pd.concat([a, b], ignore_index=True)
    # halflife largo: aquí se verifica la recuperación de parámetros, no el
    # decaimiento temporal.
    model = DixonColes(halflife_days=100000.0, xg_blend=0.0, ridge=0.005)
    model.fit(df, as_of=start + timedelta(days=420))
    return model


def test_recupera_ventaja_local_distinta_por_liga(two_league_fit):
    m = two_league_fit
    i_alta = m.params.leagues.index("liga_alta")
    i_baja = m.params.leagues.index("liga_baja")
    ha_alta = m.params.home_adv[i_alta]
    ha_baja = m.params.home_adv[i_baja]

    # Lo esencial: las distingue y en el sentido correcto.
    assert ha_alta > ha_baja + 0.15, (
        f"No separó la ventaja de local por liga: {ha_alta:.3f} vs {ha_baja:.3f}"
    )
    # Y las recupera con precisión razonable (verdad: 0.45 y 0.10).
    assert ha_alta == pytest.approx(0.45, abs=0.12)
    assert ha_baja == pytest.approx(0.10, abs=0.12)


def test_recupera_nivel_de_goles_distinto_por_liga(two_league_fit):
    m = two_league_fit
    i_alta = m.params.leagues.index("liga_alta")
    i_baja = m.params.leagues.index("liga_baja")
    assert m.params.base[i_alta] > m.params.base[i_baja], (
        "No separó el nivel de goles entre ligas"
    )
    assert m.params.base[i_alta] == pytest.approx(0.25, abs=0.15)
    assert m.params.base[i_baja] == pytest.approx(0.00, abs=0.15)


def test_equipos_de_distinta_liga_no_se_fusionan():
    """
    El bug latente que esto previene: dos ligas con un equipo del mismo nombre
    canónico compartían parámetros y partían el historial de ambos.
    """
    rng = np.random.default_rng(11)
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    a = simulate_league("mx", 8, 4, home_adv=0.40, base=0.2, start=start, rng=rng)
    b = simulate_league("br", 8, 4, home_adv=0.40, base=0.2, start=start, rng=rng)
    # Colisión deliberada de nombre entre ligas distintas.
    a["home_team"] = a["home_team"].replace({"mx_T0": "Santos"})
    a["away_team"] = a["away_team"].replace({"mx_T0": "Santos"})
    b["home_team"] = b["home_team"].replace({"br_T0": "Santos"})
    b["away_team"] = b["away_team"].replace({"br_T0": "Santos"})

    m = DixonColes(halflife_days=100000.0, xg_blend=0.0).fit(
        pd.concat([a, b], ignore_index=True), as_of=start + timedelta(days=420))

    assert team_key("mx", "Santos") in m._idx
    assert team_key("br", "Santos") in m._idx
    assert m._idx[team_key("mx", "Santos")] != m._idx[team_key("br", "Santos")], (
        "Los dos 'Santos' de ligas distintas acabaron en el mismo parámetro"
    )


def test_equipo_desconocido_cae_a_la_media_de_su_liga(two_league_fit):
    """Un recién ascendido sin historia debe predecirse como equipo promedio."""
    m = two_league_fit
    lam, mu = m.lambdas("EquipoNuevo", "OtroNuevo", "liga_alta")
    i = m.params.leagues.index("liga_alta")
    esperado_local = math.exp(m.params.base[i] + m.params.home_adv[i])
    esperado_visita = math.exp(m.params.base[i])
    assert lam == pytest.approx(esperado_local, rel=1e-6)
    assert mu == pytest.approx(esperado_visita, rel=1e-6)
    assert not m.knows("EquipoNuevo", "OtroNuevo", "liga_alta")


def test_liga_desconocida_cae_a_la_media_global(two_league_fit):
    m = two_league_fit
    lam, mu = m.lambdas("X", "Y", "liga_que_no_existe")
    esperado = math.exp(m.params.base_mean + m.params.home_adv_mean)
    assert lam == pytest.approx(esperado, rel=1e-6)
    assert mu == pytest.approx(math.exp(m.params.base_mean), rel=1e-6)


def test_predict_devuelve_probabilidades_validas(two_league_fit):
    m = two_league_fit
    out = m.predict("liga_alta_T1", "liga_alta_T2", "liga_alta")
    p = out["1x2"]
    assert p["home"] + p["draw"] + p["away"] == pytest.approx(1.0, abs=1e-9)
    assert all(0 < v < 1 for v in p.values())
    assert out["_meta"]["both_teams_known"]


def test_ventaja_local_se_refleja_en_la_prediccion(two_league_fit):
    """
    La liga con más ventaja de local debe dar más probabilidad al local.

    Se usan equipos desconocidos a propósito: así ambos caen a la media de su
    liga (ataque y defensa = 0) y lo ÚNICO que difiere entre las dos
    predicciones son los parámetros de liga. Comparar dos equipos reales
    mezclaría la diferencia de fuerza entre ellos con la de ventaja local.
    """
    m = two_league_fit
    p_alta = m.predict("cualquiera_A", "cualquiera_B", "liga_alta")["1x2"]["home"]
    p_baja = m.predict("cualquiera_A", "cualquiera_B", "liga_baja")["1x2"]["home"]
    assert p_alta > p_baja + 0.05, (
        f"La ventaja local por liga no llega a la predicción: "
        f"{p_alta:.3f} vs {p_baja:.3f}"
    )


def test_pooling_encoge_liga_pequena_hacia_la_media():
    """
    Una liga con MUY pocos partidos debe heredar la media global en vez de
    creerse su propia estimación ruidosa. Es el punto del pooling parcial.
    """
    rng = np.random.default_rng(3)
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    grande = simulate_league("grande", 12, 5, home_adv=0.35, base=0.2,
                             start=start, rng=rng)
    # Liga diminuta con ventaja de local absurda en sus pocos datos.
    pequena = simulate_league("pequena", 4, 1, home_adv=1.0, base=0.2,
                              start=start, rng=rng)
    m = DixonColes(halflife_days=100000.0, xg_blend=0.0).fit(
        pd.concat([grande, pequena], ignore_index=True),
        as_of=start + timedelta(days=420))

    i_p = m.params.leagues.index("pequena")
    i_g = m.params.leagues.index("grande")
    # La liga pequeña no debe quedarse con su 1.0 crudo: el pooling la arrastra
    # hacia la liga con datos.
    assert m.params.home_adv[i_p] < 0.9, (
        f"El pooling no encogió la liga pequeña: {m.params.home_adv[i_p]:.3f}"
    )
    assert abs(m.params.home_adv[i_p] - m.params.home_adv[i_g]) < 0.75
