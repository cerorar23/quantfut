"""
Córners de cada equipo repartidos por la supremacía del Motor A (2026-10-22).

El favorito saca más córners; el modelo anterior lo ignoraba. Lo que estas
pruebas fijan: la dirección y el tamaño del efecto, que el total no cambia, que
sin supremacía todo queda como antes y que la supremacía sale solo del modelo
propio y solo si conoce a los dos equipos.
"""
from __future__ import annotations

import math

import pytest

from qf.model import estadisticas_mercado as em
from qf.publish import escalera_datos as ed

LAM = (5.2, 4.3)


def test_sin_supremacia_nada_cambia():
    for mercado, lado, linea in (("corners_home", "over", 3.5), ("corners_away", "under", 4.5)):
        base = em.prob_total(LAM[0] if mercado == "corners_home" else LAM[1],
                             em.PARAMETROS["corners_equipo"]["phi"], linea)[lado]
        assert em.prob(mercado, LAM, lado, linea) == pytest.approx(base)
        assert em.prob(mercado, LAM, lado, linea, None) == pytest.approx(base)


def test_el_favorito_saca_mas_corners_y_el_rival_menos():
    fuerte = math.log(2.4 / 0.7)          # local muy favorito
    assert em.media_equipo("corners_home", LAM, fuerte) > LAM[0]
    assert em.media_equipo("corners_away", LAM, fuerte) < LAM[1]
    debil = -fuerte
    assert em.media_equipo("corners_home", LAM, debil) < LAM[0]
    assert em.media_equipo("corners_away", LAM, debil) > LAM[1]
    # Tamaño: con s = log(2,4/0,7) ≈ 1,23 el local sube del orden de un 25 %.
    assert 1.15 < em.media_equipo("corners_home", LAM, fuerte) / LAM[0] < 1.35


def test_la_probabilidad_sigue_a_la_media():
    s = math.log(2.0 / 0.9)
    assert em.prob("corners_home", LAM, "over", 4.5, s) > em.prob("corners_home", LAM, "over", 4.5, 0.0)
    assert em.prob("corners_away", LAM, "under", 4.5, s) > em.prob("corners_away", LAM, "under", 4.5, 0.0)


def test_el_total_no_cambia_con_la_supremacia():
    for s in (None, -1.0, 0.0, 1.3):
        assert em.prob("corners", LAM, "under", 11.5, s) == pytest.approx(em.prob("corners", LAM, "under", 11.5))


def test_visitante_mas_de_3_5_y_4_5_fuera_de_las_lineas():
    assert ("over", 3.5) not in em.LINEAS_HABILITADAS["corners_away"]
    assert ("over", 4.5) not in em.LINEAS_HABILITADAS["corners_away"]


def test_la_supremacia_sale_del_modelo_propio(monkeypatch):
    monkeypatch.setattr(ed, "query_one", lambda sql, p: {"home_lambda": 2.0, "away_lambda": 0.8, "conocido": "true"})
    assert ed.supremacia_modelo("m1") == pytest.approx(math.log(2.0 / 0.8))
    # Equipo desconocido: no hay contexto, se usa el reparto anterior.
    monkeypatch.setattr(ed, "query_one", lambda sql, p: {"home_lambda": 0.3, "away_lambda": 3.0, "conocido": "false"})
    assert ed.supremacia_modelo("m1") is None
    monkeypatch.setattr(ed, "query_one", lambda sql, p: None)
    assert ed.supremacia_modelo("m1") is None
    monkeypatch.setattr(ed, "query_one", lambda sql, p: {"home_lambda": 0, "away_lambda": 1.0, "conocido": None})
    assert ed.supremacia_modelo("m1") is None


def test_las_lineas_nuevas_solo_con_supremacia():
    nuevas = (("corners_home", "over", 4.5), ("corners_home", "under", 5.5), ("corners_home", "under", 6.5),
              ("corners_away", "under", 4.5), ("corners_away", "under", 5.5))
    for linea in nuevas:
        assert em.disponible(*linea, None) is False
        assert em.disponible(*linea, 0.3) is True
    # Las anteriores siguen disponibles sin contexto.
    assert em.disponible("corners_home", "over", 3.5, None) is True
    assert em.disponible("corners", "under", 11.5, None) is True


def test_las_baratas_no_se_publican():
    from qf.publish import alta_prob as ap
    publicadas = set(ap.CORNERS_HABILITADOS)
    for barata in (("corners_home", "over", 1.5), ("corners_home", "over", 2.5),
                   ("corners_away", "over", 1.5), ("corners_away", "under", 7.5)):
        assert barata not in publicadas
    assert em.SOLO_CON_SUPREMACIA <= publicadas


class _Acc:
    def lambdas(self, now, local, visitante, arbitro=None):
        return (5.6, 3.9)


class _Modelos:
    def de(self, liga, mercado):
        return _Acc()


def test_alta_prob_publica_la_de_cuota_mas_alta(monkeypatch):
    """Con varias líneas en 80-95 % gana la de menor probabilidad (la que más paga)."""
    from datetime import datetime, timezone

    from qf.publish import alta_prob as ap
    from qf.publish import alta_prob_datos as ad
    monkeypatch.setattr(ed, "supremacia_modelo", lambda mid: 0.9)
    monkeypatch.setattr(ed, "prudente", lambda c, filas: c)          # sin recorte de mercado
    monkeypatch.setattr(ed, "prob_mercado", lambda filas, c: c.prob)
    m = {"match_id": "m1", "league_id": "es.laliga", "home_team_id": "a", "away_team_id": "b"}
    cands, fits = ad._corners(m, datetime(2026, 10, 22, tzinfo=timezone.utc), _Modelos(), [])
    assert ("corners_away", "under", 5.5) in fits                    # nueva, con contexto
    elegido = ap.elegir(cands)
    dentro = [c for c in cands if ap.PROB_MIN <= c.prob <= ap.PROB_MAX]
    assert elegido.prob == min(c.prob for c in dentro)
    # Sin supremacía, las nuevas no entran.
    monkeypatch.setattr(ed, "supremacia_modelo", lambda mid: None)
    _, fits = ad._corners(m, datetime(2026, 10, 22, tzinfo=timezone.utc), _Modelos(), [])
    assert not (set(fits) & em.SOLO_CON_SUPREMACIA)
