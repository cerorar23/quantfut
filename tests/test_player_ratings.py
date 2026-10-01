"""
Valor por jugador (fuerza por jugador, Fase B1).

Lo que fijan: el decaimiento hace pesar más lo reciente; un jugador con pocos
minutos queda cerca de la media de su posición; el acumulador no ve lo que
todavía no se le ha añadido (punto en el tiempo).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from qf.model.player_ratings import ESTADISTICAS, MINUTOS_PREVIA, Acumulador

T0 = pd.Timestamp("2026-01-01", tz="UTC")


def _fila(pid, pos="F", minutos=90, tiros=0, nota=7.0):
    f = {e: 0 for e in ESTADISTICAS}
    f.update(player_id=pid, posicion=pos, minutos=minutos, tiros=tiros,
             nota_proveedor=nota)
    return f


def _i(nombre):
    return ESTADISTICAS.index(nombre)


def test_pocos_minutos_se_quedan_cerca_de_la_media_de_su_posicion():
    acc = Acumulador(180)
    acc.avanzar(T0)
    for pid in range(10):                        # delanteros "medios": 2 tiros/90
        acc.anadir(_fila(pid, tiros=2))
    acc.anadir(_fila(99, minutos=10, tiros=3))   # 3 tiros en 10 min = 27/90
    tasa = acc.tasas(99, "F")[_i("tiros")]      # misma hora: sin decaimiento
    esperado = (3 + MINUTOS_PREVIA * (23 / 910)) / (10 + MINUTOS_PREVIA) * 90
    assert abs(tasa - esperado) < 1e-6
    assert tasa < 3.0, "10 minutos no bastan para parecer un goleador"


def test_lo_reciente_pesa_mas():
    acc = Acumulador(180)
    acc.avanzar(T0)
    acc.anadir(_fila(1, tiros=0))
    acc.avanzar(T0 + pd.Timedelta(days=360))     # dos vidas medias
    acc.anadir(_fila(1, tiros=4))
    acc.avanzar(T0 + pd.Timedelta(days=361))
    # Sin decaimiento serían 4 tiros en 180 min = 2,0/90. Con el partido viejo
    # pesando 0,25: 4 / (90 + 22,5) · 90 ≈ 3,2.
    assert acc.tasas(1, "F")[_i("tiros")] > 2.5


def test_sin_historial_devuelve_la_media_de_su_posicion():
    acc = Acumulador(180)
    acc.avanzar(T0)
    acc.anadir(_fila(1, pos="G", tiros=0))
    acc.anadir(_fila(2, pos="F", tiros=2))
    acc.avanzar(T0 + pd.Timedelta(days=1))
    assert not acc.conocido(3)
    assert abs(acc.tasas(3, "F")[_i("tiros")] - 2.0) < 1e-9
    assert np.isnan(Acumulador(180).nota(5, "F"))


def test_no_ve_lo_que_no_se_le_ha_anadido():
    acc = Acumulador(180)
    acc.avanzar(T0)
    antes = acc.tasas(1, "F").copy()
    acc.avanzar(T0 + pd.Timedelta(days=7))
    assert np.array_equal(np.nan_to_num(antes), np.nan_to_num(acc.tasas(1, "F")))
