"""
Fija la semántica de unidades del stake.

Este archivo existe por un bug real: `kelly()` devolvía una fracción de banca
(0.0067) mientras el resto del sistema interpretaba ese número como unidades.
El efecto no era un error visible sino algo peor —el descarte
`stake <= 0.05` de `find_candidates` eliminaba TODOS los picks con edge
realista y el sistema publicaba cero picks en silencio—.

CONTRATO: 1 unidad = 1% de la banca.
"""
from __future__ import annotations

import pytest

from qf.config import settings
from qf.publish.picks import kelly

FLOOR = 0.05          # el descarte que aplica find_candidates


def stake_for(price: float, shrunk_edge: float) -> float:
    """Stake de un pick con `shrunk_edge` (fracción) a esa cuota."""
    p_shrunk = (shrunk_edge + 1.0) / price
    return kelly(p_shrunk, price, settings.kelly_fraction, settings.max_stake_units)


@pytest.mark.parametrize("price", [1.6, 1.8, 2.2, 2.5, 3.0, 3.5, 5.0])
@pytest.mark.parametrize("edge", [0.03, 0.05, 0.08, 0.15])
def test_los_edges_realistas_sobreviven_al_descarte(price, edge):
    """
    El test que habría cazado el bug: con edge del 3-15% —el rango que el
    propio MIN_EDGE_PCT admite— el pick TIENE que publicarse.
    """
    s = stake_for(price, edge)
    assert s > FLOOR, (
        f"Pick descartado con cuota {price} y edge {edge:.0%}: stake={s:.4f}. "
        "El sistema no publicaría nada."
    )


def test_una_unidad_es_uno_por_ciento_de_banca():
    """
    Kelly completo sobre una apuesta con 10% de edge a cuota 2.0:
    f = 0.10/1.0 = 10% de banca = 10 unidades. Con fracción 0.2 -> 2 unidades.
    """
    s = kelly((0.10 + 1.0) / 2.0, 2.0, fraction=0.2, cap=100.0)
    assert s == pytest.approx(2.0, rel=1e-9)


def test_kelly_completo_equivale_al_porcentaje_de_banca():
    s = kelly((0.10 + 1.0) / 2.0, 2.0, fraction=1.0, cap=100.0)
    assert s == pytest.approx(10.0, rel=1e-9)


def test_el_tope_por_apuesta_se_aplica_en_unidades():
    """Un edge enorme debe quedar recortado al tope, no dispararse."""
    s = stake_for(1.5, 2.0)          # 200% de edge: absurdo a propósito
    assert s == pytest.approx(settings.max_stake_units)


def test_sin_edge_no_hay_stake():
    assert stake_for(2.5, 0.0) == pytest.approx(0.0, abs=1e-12)


def test_edge_negativo_no_produce_apuesta():
    p = 0.9 / 2.5                     # probabilidad por debajo de la implícita
    assert kelly(p, 2.5, settings.kelly_fraction, settings.max_stake_units) == 0.0


def test_cuota_invalida_no_produce_apuesta():
    assert kelly(0.5, 1.0, 0.2, 2.0) == 0.0
    assert kelly(0.5, 0.5, 0.2, 2.0) == 0.0


def test_el_stake_crece_con_el_edge():
    stakes = [stake_for(2.5, e) for e in (0.03, 0.05, 0.10, 0.20)]
    assert stakes == sorted(stakes)
    assert stakes[0] < stakes[-1]


def test_exposicion_diaria_es_coherente_con_las_unidades():
    """
    12 picks al tope (2 u) suman 24 u = 24% de banca, por encima del tope
    diario de 10 u. Es justo el caso que `apply_portfolio_limits` debe
    recortar: si las unidades no cuadraran, ese tope no significaría nada.
    """
    total = settings.max_picks_per_day * settings.max_stake_units
    assert total > settings.max_daily_exposure
