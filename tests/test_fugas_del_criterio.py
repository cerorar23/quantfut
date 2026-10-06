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


# --- Línea de alta probabilidad (revisión final, 2026-10-06) ------------------
#
# En doble oportunidad, `1 − prob` es la probabilidad justa de Pinnacle del
# resultado EXCLUIDO, justo donde viven los picks de valor. Con 6 decimales y
# cualquier cuota blanda se recalcula el edge del criterio. La respuesta pública
# da la probabilidad a punto porcentual entero; el lote sellado y la tabla
# conservan el valor exacto.

def _decimales(x: float) -> int:
    from decimal import Decimal
    return -Decimal(repr(x)).as_tuple().exponent


def test_alta_probabilidad_publica_la_probabilidad_a_punto_entero(monkeypatch):
    from dataclasses import replace

    from qf.config import settings
    from qf.publish import alta_prob_datos as ad

    def fila(match_id, prob, fair_price):
        return {"match_id": match_id, "league_id": "br.serie_a",
                "kickoff_utc": datetime(2026, 10, 7, 20, tzinfo=timezone.utc),
                "local": "Cruzeiro", "visitante": "Sao Paulo", "market": "double_chance",
                "selection": "1X", "line": None, "prob": prob, "fair_price": fair_price,
                "ref_price": None, "ref_book": None, "batch_date": "2026-10-06",
                "chain_sha256": "ab" * 32}

    exactas = [(0.874312, 1.1437), (0.8049, 1.2424), (0.9449, 1.0583), (0.95, 1.0526)]

    def q(sql, params=()):
        if "m.kickoff_utc > now()" in sql:
            return [fila(f"m{i}", p, fp) for i, (p, fp) in enumerate(exactas)]
        return []

    monkeypatch.setattr(ad, "query", q)
    monkeypatch.setattr(ad, "settings", replace(settings, alta_prob_enabled=True))
    proximos = ad.informe_publico()["proximos"]

    assert proximos[0]["prob"] == 0.87
    assert proximos[0]["fair_price"] == round(1 / 0.87, 2)
    for p in proximos:
        assert _decimales(p["prob"]) <= 2
        assert p["fair_price"] == round(1 / p["prob"], 2)
        # Con la cuota justa y la probabilidad públicas ya no se recupera el
        # valor exacto: el 1 − prob queda a ±0,5 puntos del real.
        assert p["prob"] not in {e[0] for e in exactas[:3]}
    assert [p["prob"] for p in proximos] == [0.87, 0.80, 0.94, 0.95]
