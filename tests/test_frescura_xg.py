"""
`worldfootballR_data` dejó de publicar en 2024-25 y el job semanal respondió
`ok` con 0 filas durante un año. Este chequeo alarma cuando una liga con
partidos jugados lleva demasiado sin xG. Las ligas ya paradas el 2-oct-2026
quedan reconocidas hasta una fecha fija (decisión pendiente del usuario): sin
caducidad, el reconocimiento escondería el problema para siempre.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from qf.ingest import health

HOY = datetime(2026, 10, 3, tzinfo=timezone.utc)


def _fila(liga, ult_jugado_dias, ult_xg_dias, hoy=HOY):
    return {"league_id": liga,
            "ult_jugado": hoy - timedelta(days=ult_jugado_dias),
            "ult_xg": None if ult_xg_dias is None else hoy - timedelta(days=ult_xg_dias)}


def _chequeo(monkeypatch, filas, hoy=HOY):
    monkeypatch.setattr(health, "query", lambda sql, params=None: filas)
    return health.check_xg_freshness(now=hoy)


def test_liga_al_dia_pasa(monkeypatch):
    ok, msg = _chequeo(monkeypatch, [_fila("xx.nueva", 2, 6)])
    assert ok


def test_liga_nueva_parada_falla_aunque_haya_reconocidas(monkeypatch):
    ok, msg = _chequeo(monkeypatch, [_fila("xx.nueva", 2, 60),
                                     _fila("gb.premier_league", 2, 380)])
    assert not ok and "xx.nueva" in msg


def test_liga_sin_ningun_xg_cuenta_como_parada(monkeypatch):
    ok, msg = _chequeo(monkeypatch, [_fila("xx.nueva", 2, None)])
    assert not ok


def test_las_reconocidas_no_fallan_antes_de_la_fecha(monkeypatch):
    ok, msg = _chequeo(monkeypatch, [_fila("gb.premier_league", 2, 380)])
    assert ok and "reconocid" in msg and "gb.premier_league" in msg


def test_las_reconocidas_fallan_al_caducar(monkeypatch):
    despues = datetime.combine(health.XG_PARADO_RECONOCIDO_HASTA, datetime.min.time(),
                               tzinfo=timezone.utc) + timedelta(days=1)
    ok, msg = _chequeo(monkeypatch, [_fila("gb.premier_league", 2, 410, despues)],
                       hoy=despues)
    assert not ok


def test_sin_partidos_recientes_no_alarma(monkeypatch):
    # En parón o fuera de temporada no hay xG que esperar.
    ok, msg = _chequeo(monkeypatch, [_fila("xx.nueva", 40, 300)])
    assert ok


def test_el_chequeo_esta_en_la_lista_diaria():
    assert any(fn is health.check_xg_freshness for _, fn in health.CHECKS)
    assert isinstance(health.XG_PARADO_RECONOCIDO_HASTA, date)
