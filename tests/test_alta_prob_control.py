"""Control de calidad e historial de la línea de alta probabilidad."""
from datetime import datetime, timedelta, timezone

import pytest

from qf.publish import alta_prob as ap

T0 = datetime(2026, 1, 5, 20, 0, tzinfo=timezone.utc)


def _filas(n, prob, tasa, market="double_chance", semanas=10, ref=None):
    aciertos = round(n * tasa)
    return [{"market": market, "prob": prob, "ref_price": ref,
             "outcome": "win" if i < aciertos else "loss",
             "kickoff_utc": T0 + timedelta(weeks=i % semanas)}
            for i in range(n)]


def test_sin_muestra_no_bloquea():
    assert ap.control([])["bloqueados"] == []
    assert ap.control(_filas(40, 0.87, 0.5))["bloqueados"] == []


def test_promete_de_mas_bloquea_todo_y_su_mercado():
    out = ap.control(_filas(120, 0.87, 0.60))
    assert "todo" in out["bloqueados"] and "double_chance" in out["bloqueados"]


def test_cumpliendo_no_bloquea():
    assert ap.control(_filas(300, 0.87, 0.87))["bloqueados"] == []


def test_solo_el_mercado_que_falla():
    # Medido: conjunto IC95 [−0,6; +1,2] pts (no bloquea), goles [−36; −26].
    filas = _filas(400, 0.87, 0.92) + _filas(60, 0.86, 0.55, market="totals")
    out = ap.control(filas)
    assert out["bloqueados"] == ["totals"]


def test_sin_ocho_semanas_no_hay_intervalo_ni_bloqueo():
    out = ap.control(_filas(120, 0.87, 0.40, semanas=3))
    assert out["bloqueados"] == []
    assert any("semanas" in m for m in out["motivos"])


def test_historial():
    filas = _filas(20, 0.85, 0.90, ref=1.20) + _filas(10, 0.90, 0.80, market="h2h")
    h = ap.historial(filas)
    assert h["n"] == 30 and h["aciertos"] == 26
    assert h["acierto_prometido"] == pytest.approx(86.7, abs=0.05)
    assert h["acierto_real"] == pytest.approx(86.7, abs=0.05)
    assert h["por_mercado"]["h2h"]["n"] == 10
    assert h["rendimiento_ref"]["n"] == 20
    assert h["rendimiento_ref"]["roi"] == pytest.approx((18 * 0.2 - 2) / 20 * 100)
    assert h["diferencia_ic95"] is not None


def test_historial_vacio():
    h = ap.historial([])
    assert h["n"] == 0 and h["acierto_real"] is None and h["por_mercado"] == {}
