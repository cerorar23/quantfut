"""
Ajuste de Dixon-Coles: gradiente exacto, convergencia y equipos sin datos.

Auditoría del 2026-10-21: con diferencias finitas sobre ~800 parámetros el
optimizador agotaba el tope de evaluaciones sin converger, y la suma cero
uniforme usaba a los equipos sin datos como holgura (ataques de hasta ±2,4).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from qf.model.dixon_coles import DixonColes

AHORA = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _liga(liga, n_equipos, jornadas, desde, semilla, prefijo="T"):
    rng = np.random.default_rng(semilla)
    equipos = [f"{prefijo}{i}" for i in range(n_equipos)]
    fuerza = rng.normal(0, 0.3, n_equipos)
    filas = []
    for j in range(jornadas):
        for a in range(n_equipos):
            for b in range(n_equipos):
                if a != b:
                    filas.append({
                        "kickoff_utc": desde + timedelta(days=7 * j + a % 3),
                        "league_id": liga, "home_team": equipos[a], "away_team": equipos[b],
                        "home_goals": float(rng.poisson(1.5 * np.exp(fuerza[a] - fuerza[b]))),
                        "away_goals": float(rng.poisson(1.1 * np.exp(fuerza[b] - fuerza[a]))),
                        "home_xg": float(rng.gamma(4, 0.37)), "away_xg": float(rng.gamma(4, 0.28)),
                    })
    return pd.DataFrame(filas)


@pytest.fixture(scope="module")
def datos():
    activa = _liga("L1", 8, 10, AHORA - timedelta(days=300), 0)
    otra = _liga("L2", 6, 10, AHORA - timedelta(days=300), 1)
    # Equipos que no juegan desde hace ocho años: sin muestra efectiva.
    fantasmas = _liga("L1", 5, 3, AHORA - timedelta(days=8 * 365), 2, prefijo="F")
    return pd.concat([activa, otra, fantasmas], ignore_index=True)


@pytest.fixture(scope="module")
def modelo(datos):
    return DixonColes(halflife_days=270.0, xg_blend=0.65).fit(datos, as_of=AHORA)


def test_el_gradiente_analitico_coincide_con_diferencias_finitas(modelo):
    rng = np.random.default_rng(3)
    p = np.concatenate([np.array(modelo.params.attack), np.array(modelo.params.defence),
                        np.array(modelo.params.home_adv), np.array(modelo.params.base),
                        np.array(modelo.params.strength), [modelo.params.rho]])
    p = p + rng.normal(0, 0.05, len(p))
    p[-1] = -0.05
    _, g = modelo._objetivo(p)
    for i in rng.choice(len(p), 20, replace=False).tolist() + [len(p) - 1]:
        e = np.zeros_like(p)
        e[i] = 1e-6
        num = (modelo._objetivo(p + e)[0] - modelo._objetivo(p - e)[0]) / 2e-6
        assert num == pytest.approx(g[i], rel=1e-4, abs=1e-4)


def test_el_ajuste_converge(modelo):
    assert modelo.params.converged is True


def test_los_equipos_sin_datos_no_quedan_extremos(modelo):
    eff = np.array(modelo.params.effective_n)
    atk = np.array(modelo.params.attack)
    dfn = np.array(modelo.params.defence)
    sin_datos = eff < 0.05
    assert sin_datos.sum() == 5
    assert np.abs(atk[sin_datos]).max() < 0.2
    assert np.abs(dfn[sin_datos]).max() < 0.2


def test_la_suma_cero_la_fijan_los_equipos_que_juegan(modelo):
    eff = np.array(modelo.params.effective_n)
    atk = np.array(modelo.params.attack)
    ligas = np.array(modelo.params.team_leagues)
    for lg in ("L1", "L2"):
        m = ligas == lg
        assert abs(np.sum(eff[m] * atk[m]) / eff[m].sum()) < 1e-3


def test_el_ridge_se_mide_en_partidos_recientes(datos):
    """Duplicar el histórico viejo no puede cambiar cuánto se encoge un equipo reciente."""
    a = DixonColes(halflife_days=270.0, xg_blend=0.65).fit(datos, as_of=AHORA)
    viejo = _liga("L2", 6, 30, AHORA - timedelta(days=12 * 365), 9, prefijo="V")
    b = DixonColes(halflife_days=270.0, xg_blend=0.65).fit(
        pd.concat([datos, viejo], ignore_index=True), as_of=AHORA)
    ia, ib = a._idx["L1||T0"], b._idx["L1||T0"]
    assert a.params.attack[ia] == pytest.approx(b.params.attack[ib], abs=0.02)


def test_artefacto_anterior_conserva_su_objetivo(tmp_path, modelo):
    ruta = tmp_path / "m.pkl"
    modelo.save(str(ruta))
    cargado = DixonColes.load(str(ruta))
    assert cargado.ridge_partidos == modelo.ridge_partidos
    assert cargado.lambdas("T0", "T1", "L1") == modelo.lambdas("T0", "T1", "L1")
