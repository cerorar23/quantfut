"""
Auditoría de la fase 3 (2026-10-03, decisión del usuario).

`market_consensus` es la probabilidad justa del mercado sin margen: con ella y
la cuota de cualquier casa se reconstruye el criterio de picks entero, la
misma razón por la que `/fair-price` pasó a `/v1` el 28-sep.
  - `/matches/{id}` (público) ya no la devuelve; `/v1` sí.
  - Los lotes sellados dejan de llevarla desde el 3-oct-2026 (opción b). Los
    anteriores NO se tocan: regenerarlos desde la base tiene que dar el mismo
    hash que el día que se sellaron.
  - `/openapi.json` no se sirve: listaba las rutas de `/admin` y `/v1`, que
    responden 404 justamente para no confirmar que existen.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

PRED = {"prediction_id": "p1", "model_version": "v", "generated_at": "2026-10-02",
        "markets": {"1x2": {"home": 0.6, "draw": 0.2, "away": 0.2}, "totals": {}},
        "market_consensus": {"home": 0.64, "draw": 0.19, "away": 0.17},
        "confidence_tier": "high", "data_completeness": 1.0}
PARTIDO = {"match_id": "m1", "league_id": "us.mls", "season": "2627",
           "kickoff_utc": datetime(2026, 10, 2, tzinfo=timezone.utc),
           "status": "finished", "home_goals": 1, "away_goals": 0,
           "local": "A", "visitante": "B"}


def _cliente(monkeypatch):
    from qf.api import main

    def query_one(sql, params=None):
        if "FROM predictions" in sql:
            # Lo que devuelva la consulta es lo que se publica: si pide la
            # columna, la fila la trae.
            return {k: v for k, v in PRED.items()
                    if k != "market_consensus" or "market_consensus" in sql}
        if "FROM picks" in sql:
            return None
        return PARTIDO

    monkeypatch.setattr(main, "r", None)
    monkeypatch.setattr(main.ratelimit, "rate_limited", lambda *a, **k: False)
    monkeypatch.setattr(main, "query_one", query_one)
    return main, TestClient(main.app)


def test_la_ficha_publica_no_publica_el_precio_justo(monkeypatch):
    _, cliente = _cliente(monkeypatch)
    pred = cliente.get("/matches/m1").json()["prediction"]
    assert "market_consensus" not in pred
    assert pred["markets"]["1x2"]["home"] == 0.6      # la opinión del modelo sigue


def test_openapi_no_se_sirve(monkeypatch):
    main, cliente = _cliente(monkeypatch)
    assert main.app.openapi_url is None
    assert cliente.get("/openapi.json").status_code == 404


def _sql_del_lote(monkeypatch, dia):
    from qf.publish import hashchain
    sqls = []
    monkeypatch.setattr(hashchain, "query",
                        lambda sql, params=None: sqls.append(sql) or [])
    hashchain._collect(dia)
    return sqls[0]


def test_los_lotes_nuevos_no_llevan_el_precio_justo(monkeypatch):
    from qf.publish import hashchain
    assert "market_consensus" not in _sql_del_lote(
        monkeypatch, hashchain.LOTE_SIN_CONSENSO_DESDE)


def test_los_lotes_anteriores_se_regeneran_igual(monkeypatch):
    assert "market_consensus" in _sql_del_lote(monkeypatch, date(2026, 10, 2))
