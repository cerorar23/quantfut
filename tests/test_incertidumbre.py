"""
Zona de abstención y encogimiento medido.

Lo que hay que demostrar no es que el número salga: es que el número DISTINGUE.
Un encogimiento medido que encoja igual a un equipo con veinte partidos
recientes y a uno con tres no vale más que la constante de 0,55 que sustituye.

Los cuatro tests van en ese orden:
  1. el error estándar baja cuando hay más muestra;
  2. la incertidumbre del edge se hereda de ahí;
  3. un edge dentro del ruido se ABSTIENE, uno sólido no.

El módulo ya no participa en la selección de picks (2026-09-23: el edge sale
del precio de Pinnacle, no del modelo). Se conserva como herramienta de
medición, y con él estos tests.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from qf.model.dixon_coles import DixonColes
from qf.model.uncertainty import edge_uncertainty, lambda_draws


def _liga(n_equipos: int, jornadas: int, desde: datetime, semilla: int = 0):
    rng = np.random.default_rng(semilla)
    equipos = [f"T{i}" for i in range(n_equipos)]
    filas = []
    for j in range(jornadas):
        for a in range(n_equipos):
            for b in range(n_equipos):
                if a == b:
                    continue
                filas.append({
                    "kickoff_utc": desde + timedelta(days=7 * j),
                    "league_id": "L1", "home_team": equipos[a],
                    "away_team": equipos[b],
                    "home_goals": float(rng.poisson(1.5)),
                    "away_goals": float(rng.poisson(1.1)),
                    "home_xg": np.nan, "away_xg": np.nan,
                })
    return pd.DataFrame(filas)


@pytest.fixture(scope="module")
def modelo():
    """Liga con historia larga y otra con historia corta, en el mismo ajuste."""
    ahora = datetime(2026, 9, 1, tzinfo=timezone.utc)
    largo = _liga(6, 20, ahora - timedelta(days=150), semilla=0)
    # Cuatro equipos que solo aparecen en las últimas dos jornadas.
    corto = _liga(4, 2, ahora - timedelta(days=20), semilla=1)
    corto["home_team"] = "N" + corto["home_team"]
    corto["away_team"] = "N" + corto["away_team"]
    df = pd.concat([largo, corto], ignore_index=True)
    m = DixonColes(halflife_days=180.0, xg_blend=0.0)
    m.fit(df, as_of=ahora)
    return m


def test_mas_muestra_menos_error_estandar(modelo):
    from qf.model.uncertainty import _se
    se_largo, _ = _se(modelo, "T0", "L1")
    se_corto, _ = _se(modelo, "NT0", "L1")
    assert se_largo > 0 and se_corto > 0
    assert se_corto > se_largo, "menos partidos tiene que dar MÁS incertidumbre"


def test_el_equipo_sin_muestra_no_puede_ser_el_mejor_conocido():
    """
    El fallo que tuvo la primera versión, fijado para que no vuelva.

    Con el estimador sándwich a secas, los seis equipos con el error estándar
    MÁS PEQUEÑO del modelo entrenado sobre datos reales eran los seis con
    muestra efectiva 0,0000. Es correcto en su propio marco —sin muestra no hay
    variabilidad muestral— y es exactamente lo contrario de lo que hace falta:
    ese parámetro lo fija el ridge, y un prior no es conocimiento.
    """
    ahora = datetime(2026, 9, 1, tzinfo=timezone.utc)
    activa = _liga(6, 20, ahora - timedelta(days=150), semilla=0)
    zombi = _liga(4, 4, ahora - timedelta(days=8 * 365), semilla=1)
    zombi["home_team"] = "Z" + zombi["home_team"]
    zombi["away_team"] = "Z" + zombi["away_team"]
    m = DixonColes(halflife_days=180.0, xg_blend=0.0)
    m.fit(pd.concat([activa, zombi], ignore_index=True), as_of=ahora)

    se = np.array(m.params.se_attack)
    eff = np.array(m.params.effective_n)
    peor_medido = int(np.argmin(eff))
    mejor_medido = int(np.argmax(eff))
    assert eff[peor_medido] < 0.01 and eff[mejor_medido] > 5

    assert se[peor_medido] > se[mejor_medido], (
        "el equipo sin muestra NO puede tener menos error estándar "
        "que el mejor medido")
    # Y la incertidumbre tiene que ser lo bastante grande como para que la
    # abstención se dispare sola, sin reglas aparte. Desde 2026-10-21 el ridge
    # es un prior de verdad (`ridge_partidos`), así que sin datos el error
    # estándar es el del prior, 1/sqrt(2·ridge_partidos) = 1 en log-ataque (un
    # factor e), y no infinito: muchas veces el del mejor medido.
    assert se[peor_medido] >= 0.99 / np.sqrt(2 * m.ridge_partidos)
    assert se[peor_medido] > 5 * se[mejor_medido]


def test_equipo_desconocido_es_incierto_no_certero(modelo):
    lams, mus = lambda_draws(modelo, "NoExiste", "T1", "L1", n_draws=16)
    assert np.isnan(lams).all(), "sin parámetros no se puede afirmar nada"


def test_la_dispersion_del_edge_hereda_la_del_parametro(modelo):
    """Misma cuota y mismo mercado: solo cambia de quién se sabe menos."""
    p_largo = modelo.predict("T0", "T1", "L1")["1x2"]["home"]
    u_largo = edge_uncertainty(modelo, "T0", "T1", "h2h", "home", None,
                               1.35 / p_largo, "L1", n_draws=400)
    p_corto = modelo.predict("NT0", "NT1", "L1")["1x2"]["home"]
    u_corto = edge_uncertainty(modelo, "NT0", "NT1", "h2h", "home", None,
                               1.35 / p_corto, "L1", n_draws=400)
    assert u_corto.edge_sd > u_largo.edge_sd


def test_abstencion_frente_a_ventaja_solida(modelo):
    """Una cuota apenas por encima de la justa no sobrevive al ruido."""
    p = modelo.predict("T0", "T1", "L1")["1x2"]["home"]
    justa = 1.0 / p

    ruido = edge_uncertainty(modelo, "T0", "T1", "h2h", "home", None,
                             justa * 1.005, "L1", n_draws=600)
    assert ruido.abstain
    assert ruido.shrinkage == 0.0

    solida = edge_uncertainty(modelo, "T0", "T1", "h2h", "home", None,
                              justa * 1.60, "L1", n_draws=600)
    assert not solida.abstain
    assert 0.0 < solida.shrinkage <= 1.0
    assert solida.edge_floor > 0


def test_el_encogimiento_medido_premia_a_quien_esta_mejor_medido(modelo):
    """Al mismo edge bruto, el equipo con más muestra se encoge menos."""
    def _shrink(h, a, factor=1.30):
        p = modelo.predict(h, a, "L1")["1x2"]["home"]
        return edge_uncertainty(modelo, h, a, "h2h", "home", None,
                                factor / p, "L1", n_draws=600).shrinkage

    assert _shrink("T0", "T1") > _shrink("NT0", "NT1")
