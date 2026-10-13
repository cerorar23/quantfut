"""Ventana del pronóstico: cada partido se calcula el mismo día, a las 03:00 de México."""
from datetime import datetime, timedelta, timezone

import pytest

from qf.api import mobile
from qf.publish import (alta_prob as ap, alta_prob_datos, alta_prob_ext, daily, escalera_datos,
                        parley_datos, ventana)

UTC = timezone.utc


def utc(*a):
    return datetime(*a, tzinfo=UTC)


def test_un_partido_de_la_tarde_se_calcula_ese_dia_a_las_05_de_mexico():
    # 14:00 en México = 20:00 UTC → corrida de las 03:00 MX (09:00 UTC) de ese día.
    assert ventana.desbloqueo(utc(2026, 10, 14, 20)) == utc(2026, 10, 14, 9)


def test_un_partido_de_madrugada_se_calcula_el_dia_anterior():
    # 03:30 MX (nada en ligas del modelo): no hay margen tras la corrida del día.
    assert ventana.desbloqueo(utc(2026, 10, 14, 9, 30)) == utc(2026, 10, 13, 9)
    # 04:00 MX justo: ya hay una hora de margen.
    assert ventana.desbloqueo(utc(2026, 10, 14, 10)) == utc(2026, 10, 14, 9)
    assert ventana.desbloqueo(utc(2026, 10, 14, 9, 59, 59)) == utc(2026, 10, 13, 9)


def test_los_horarios_europeos_de_mediodia_entran_el_mismo_dia():
    # Serie A 12:30 CEST (10:30 UTC), Premier 12:30 BST (11:30 UTC), Ligue 1 13:00 CEST (11:00 UTC).
    for k in (utc(2026, 10, 18, 10, 30), utc(2026, 10, 17, 11, 30), utc(2026, 10, 18, 11)):
        assert ventana.desbloqueo(k) == k.replace(hour=9, minute=0)


def test_la_ventana_de_la_corrida_llega_hasta_el_margen_del_dia_siguiente():
    ahora = utc(2026, 10, 13, 9, 0, 30)              # corrida de las 03:00 MX
    assert ventana.proxima_corrida(ahora) == utc(2026, 10, 14, 9)
    fin = ventana.fin_ventana(ahora)
    assert fin < utc(2026, 10, 14, 10) and fin > utc(2026, 10, 14, 9, 59)
    # Corrida lanzada a mano antes de las 03:00 MX: solo cubre hasta las 04:00 MX de hoy.
    assert ventana.proxima_corrida(utc(2026, 10, 13, 7)) == utc(2026, 10, 13, 9)


def test_el_tope_no_amplia_el_horizonte_de_cada_generador():
    ahora = utc(2026, 10, 13, 9, 0, 30)
    assert ventana.fin_ventana(ahora, timedelta(hours=3)) == ahora + timedelta(hours=3)
    assert ventana.fin_ventana(ahora, timedelta(hours=36)) == ventana.fin_ventana(ahora)


def test_cada_partido_cae_en_la_ventana_de_una_sola_corrida():
    """Las ventanas de corridas consecutivas se reparten los partidos sin huecos ni solapes."""
    inicio = utc(2026, 10, 10)
    for horas in range(0, 24 * 8, 1):
        k = inicio + timedelta(hours=horas, minutes=30)
        corrida = ventana.desbloqueo(k)
        ahora = corrida + timedelta(seconds=30)
        assert k <= ventana.fin_ventana(ahora), k
        assert k > ventana.fin_ventana(ahora - timedelta(days=1)), k


def test_mexico_es_utc_menos_6_todo_el_año():
    for mes in (1, 7, 10):
        assert datetime(2026, mes, 15, 9, tzinfo=UTC).astimezone(ventana.MEXICO).hour == 3


def test_el_servidor_marca_cuando_se_calcula_cada_partido():
    assert mobile.pronostico_desde('2026-10-14T20:00:00+00:00') == '2026-10-14T09:00:00+00:00'
    assert mobile.pronostico_desde(utc(2026, 10, 14, 20)) == '2026-10-14T09:00:00+00:00'
    assert mobile.pronostico_desde('2026-10-14T20:00:00Z') == '2026-10-14T09:00:00+00:00'
    assert mobile.pronostico_desde(None) is None
    assert mobile.pronostico_desde('no es fecha') is None


def _params(monkeypatch, modulo, funcion, *args):
    capturado = []
    monkeypatch.setattr(modulo, 'query', lambda s, p=None: capturado.append((s, p)) or [])
    funcion(*args)
    return capturado[0]


def test_la_prediccion_diaria_usa_la_ventana_del_dia(monkeypatch):
    sql, params = _params(monkeypatch, daily, daily._upcoming)
    assert 'BETWEEN now() AND %s' in sql
    assert params[0] > datetime.now(UTC)
    sql, params = _params(monkeypatch, daily, daily._sharp_only_upcoming)
    assert 'BETWEEN now() AND %s' in sql and params[0] > datetime.now(UTC)


@pytest.mark.parametrize('modulo,funcion', [
    (alta_prob_datos, alta_prob_datos._partidos), (alta_prob_ext, alta_prob_ext._partidos),
    (escalera_datos, escalera_datos._partidos), (parley_datos, parley_datos._partidos)])
def test_los_generadores_de_pronosticos_respetan_la_misma_ventana(monkeypatch, modulo, funcion):
    ahora = utc(2026, 10, 13, 9, 0, 30)
    _, params = _params(monkeypatch, modulo, funcion, ahora)
    assert params[1] == ventana.fin_ventana(ahora, params[1] - ahora) or \
        params[1] <= ventana.fin_ventana(ahora)
    assert params[1] < utc(2026, 10, 14, 10)
