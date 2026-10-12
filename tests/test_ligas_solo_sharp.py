"""
Ligas "solo sharp" (`leagues.model_enabled = FALSE`, db/023): LaLiga 2 y
Serie B entran por el criterio de precio, que no necesita el modelo.

Lo que fijan estos tests:
  - FUERA de lo que alimenta al modelo o a la cadena sellada: la predicción
    diaria (sellaría predicciones sin base, inmutables), el entrenamiento y su
    comprobación de frescura, alineaciones, bajas y xG;
  - DENTRO de lo que usa el criterio: calendario, cuotas de API-Football y
    sombra (siguen filtrando solo por `active`);
  - en The Odds API solo pagan el 1X2: 1 crédito por llamada, no 3.
"""
from __future__ import annotations

import pytest

from qf.config import settings


def _sql_de(monkeypatch, modulo, funcion, *args, attr="query"):
    capturado = []

    def falso(sql, params=None):
        capturado.append(sql)
        return [] if attr == "query" else None

    monkeypatch.setattr(modulo, attr, falso)
    try:
        funcion(*args)
    except Exception:  # noqa: BLE001 — solo interesa la consulta emitida
        pass
    assert capturado, f"{funcion.__name__} no consultó la base"
    return capturado[0]


def test_la_prediccion_diaria_solo_ve_ligas_del_modelo(monkeypatch):
    from qf.publish import daily
    sql = _sql_de(monkeypatch, daily, daily._upcoming)
    assert "model_enabled" in sql
    # Y en copa, la liga DOMÉSTICA de cada equipo también tiene que tener modelo.
    assert "lh.league_id = th.league_id AND lh.model_enabled" in sql
    assert "la.league_id = ta.league_id AND la.model_enabled" in sql


def test_el_entrenamiento_solo_ve_ligas_del_modelo(monkeypatch):
    from qf.model import train
    sql = _sql_de(monkeypatch, train, train.load_training_data)
    assert "model_enabled" in sql
    for a, t in (("lg", "m"), ("lh", "th"), ("la", "ta")):
        assert f"{a}.league_id = {t}.league_id" in sql
        assert f"AND ({a}.model_enabled OR {a}.league_id = ANY(%s::text[]))" in sql


def test_incluir_solo_abre_las_ligas_pedidas(monkeypatch):
    """
    Para entrenar el modelo que activará unas ligas antes de encender su
    interruptor (2026-10-11). Sin `incluir` la lista va vacía: nada cambia.
    """
    from qf.model import train
    parametros = []
    monkeypatch.setattr(train, "query", lambda sql, params=None: parametros.append(params) or [])
    train.load_training_data()
    train.load_training_data(incluir=["es.laliga2"])
    assert parametros[0][1:4] == ([], [], [])
    assert parametros[1][1:4] == (["es.laliga2"],) * 3


def test_la_frescura_del_bootstrap_mira_lo_mismo_que_el_entrenamiento(monkeypatch):
    from qf.model import train
    consultas = []
    monkeypatch.setattr(train, "query_one",
                        lambda sql, params=None: consultas.append(sql) or None)
    train.bootstrap_status()
    assert any("model_enabled" in q for q in consultas[1:]), \
        "si no, un cierre de LaLiga 2 daría por fresco un mercado que el modelo no ve"


@pytest.mark.parametrize("modulo", ["lineups", "injuries"])
def test_alineaciones_y_bajas_no_gastan_cuota_en_ligas_sin_modelo(monkeypatch, modulo):
    import importlib
    m = importlib.import_module(f"qf.ingest.{modulo}")
    sql = _sql_de(monkeypatch, m, m.pending_matches)
    # db/052: tampoco en ligas con modelo pero captura reducida.
    assert "model_enabled" in sql and "captura_completa" in sql


def test_el_xg_no_recorre_ligas_sin_modelo(monkeypatch):
    from qf.ingest import xg_worldfootball as xg
    assert "model_enabled" in _sql_de(monkeypatch, xg, xg.run)


@pytest.mark.parametrize("modulo,funcion", [
    ("qf.ingest.af_odds", "_pending"),
    ("qf.publish.shadow_sharp", "capture"),
    ("qf.ingest.fixtures", "run"),
])
def test_el_criterio_si_ve_las_ligas_solo_sharp(monkeypatch, modulo, funcion):
    import importlib
    m = importlib.import_module(modulo)
    f = getattr(m, funcion)
    args = () if funcion != "_pending" else (__import__("datetime").datetime.now(),)
    sql = _sql_de(monkeypatch, m, f, *args)
    assert "active" in sql and "model_enabled" not in sql


@pytest.mark.parametrize("habilitado,completa,esperado", [
    (True, True, settings.odds_api_markets), (False, False, "h2h"),
    (None, None, settings.odds_api_markets),
    # db/052: activar el modelo en una liga NO triplica lo que se paga.
    (True, False, "h2h")])
def test_the_odds_api_solo_paga_1x2_en_ligas_solo_sharp(monkeypatch, habilitado, completa,
                                                        esperado):
    from qf.ingest import odds_worker
    fila = (None if habilitado is None
            else {"model_enabled": habilitado, "captura_completa": completa})
    monkeypatch.setattr(odds_worker, "query_one", lambda sql, params=None: fila)
    assert odds_worker._markets_for("soccer_spain_segunda_division") == esperado
