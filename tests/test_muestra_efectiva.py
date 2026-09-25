"""
Un equipo puede estar en el modelo y aun así no estar MEDIDO.

El caso que lo destapó (2026-09-22, demostración con cuotas reales de la
Premier): Hull vuelve a primera tras no jugarla desde 2017. Tiene cientos de
partidos en la base, así que:

  - `knows()` decía True, porque está en el índice;
  - `_confidence()` le daba tier `high`, porque cuenta partidos de toda la vida;
  - `lambdas()` NO lo llevaba a la media de su liga, porque sí tiene
    parámetros: unos que con media vida de 180 días no vienen de sus datos
    sino del ridge y del centrado de la liga, y que son extremos.

Resultado: probabilidad 0,9061 contra un mercado que decía 0,4659, "edge" del
97% y el stake MÁXIMO. Ninguna de las tres guardas existentes lo veía:
`knows()` daba True, `EDGE_SHRINKAGE` dejaba el edge en 53% y `MAX_STAKE_UNITS`
recortaba justo a lo que ya se estaba apostando.

Lo que distingue el caso peligroso del inofensivo es la muestra EFECTIVA: la
suma de los pesos de decaimiento, no el número de partidos. Un equipo que nunca
jugó (ascendido de verdad) tiene 0 y cae a la media de su liga, que es seguro.
Uno que jugó hace ocho años tiene 0,0000 de muestra efectiva y un parámetro
extremo, que no lo es.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from qf.config import settings
from qf.model.dixon_coles import DixonColes
from qf.publish.daily import _confidence


def _liga(n_equipos=8, jornadas=14, desde=None, semilla=0):
    """Liga sintética con partidos de ida y vuelta."""
    rng = np.random.default_rng(semilla)
    desde = desde or datetime(2024, 1, 1, tzinfo=timezone.utc)
    equipos = [f"T{i}" for i in range(n_equipos)]
    filas = []
    for j in range(jornadas):
        for a in range(n_equipos):
            for b in range(n_equipos):
                if a == b:
                    continue
                filas.append({
                    "kickoff_utc": desde + timedelta(days=7 * j),
                    "league_id": "L1", "home_team": equipos[a], "away_team": equipos[b],
                    "home_goals": float(rng.poisson(1.5)),
                    "away_goals": float(rng.poisson(1.1)),
                    "home_xg": np.nan, "away_xg": np.nan,
                })
    return pd.DataFrame(filas), equipos


def _modelo_con_zombi():
    """Una liga activa más un equipo que dejó de jugar hace ocho años."""
    ahora = datetime(2026, 9, 1, tzinfo=timezone.utc)
    reciente, equipos = _liga(desde=ahora - timedelta(days=200))
    viejo, _ = _liga(jornadas=6, desde=ahora - timedelta(days=8 * 365), semilla=1)
    viejo["home_team"] = viejo["home_team"].replace({"T0": "Zombi"})
    viejo["away_team"] = viejo["away_team"].replace({"T0": "Zombi"})
    df = pd.concat([viejo, reciente], ignore_index=True)
    m = DixonColes(halflife_days=180.0, xg_blend=0.0)
    m.fit(df, as_of=ahora)
    return m, equipos


@pytest.fixture(scope="module")
def modelo():
    return _modelo_con_zombi()


def test_el_zombi_esta_en_el_indice_pero_sin_muestra(modelo):
    m, equipos = modelo
    assert m.effective_n("Zombi", "L1") < 0.5
    assert m.effective_n(equipos[1], "L1") > 5.0


def test_knows_rechaza_muestra_insuficiente(modelo):
    m, equipos = modelo
    assert m.knows(equipos[1], equipos[2], "L1")
    assert not m.knows(equipos[1], "Zombi", "L1")
    assert not m.knows("Zombi", equipos[1], "L1")


def test_la_prediccion_expone_la_muestra(modelo):
    m, equipos = modelo
    meta = m.predict(equipos[1], "Zombi", "L1")["_meta"]
    assert meta["away_effective_n"] == pytest.approx(m.effective_n("Zombi", "L1"))
    assert not meta["both_teams_known"]


def test_confianza_baja_aunque_el_historial_sea_largo():
    """El historial de toda la vida no puede sobreescribir la muestra efectiva."""
    largo = 400
    assert _confidence(largo, largo, True) == "high"
    assert _confidence(largo, largo, True,
                       home_eff=20.0,
                       away_eff=settings.min_effective_matches - 0.1) == "low"
    assert _confidence(largo, largo, True, home_eff=20.0, away_eff=20.0) == "high"


def test_artefacto_sin_el_campo_no_bloquea(modelo):
    """Un modelo viejo no tiene el dato: no puede afirmar que falte muestra."""
    m, equipos = modelo
    m.params.effective_n = []
    assert m.effective_n("Zombi", "L1") == float("inf")
    assert m.knows(equipos[1], "Zombi", "L1")
