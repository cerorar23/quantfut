"""El chequeo diario ve el proveedor de resultados y de cuotas activos (auditoría del 24-oct-2026)."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from qf.ingest import health

NOW = datetime(2026, 10, 25, 7, 0, tzinfo=timezone.utc)


def fake_query(ultimo, jugados, horas):
    def q(sql, params=()):
        if "max(result_recorded_at)" in sql:
            return [dict(ultimo=ultimo, jugados=jugados)]
        return [dict(h=horas)]
    return q


def test_resultados_parados_con_partidos_jugados_falla(monkeypatch):
    monkeypatch.setattr(health, "query", fake_query(NOW - timedelta(days=2), 76, 58.0))
    ok, msg = health.check_results_freshness()
    assert not ok and "58 h" in msg and "76" in msg


def test_resultados_al_dia_y_sin_partidos(monkeypatch):
    monkeypatch.setattr(health, "query", fake_query(NOW, 30, 2.0))
    assert health.check_results_freshness()[0]
    monkeypatch.setattr(health, "query", fake_query(None, 0, 0))
    assert health.check_results_freshness()[0]


def test_frescura_de_cuotas_usa_el_proveedor_activo(monkeypatch):
    import qf.config as cfg
    monkeypatch.setattr(cfg, "settings", SimpleNamespace(odds_provider="propline"))
    vistos = []
    def q(sql, params=()):
        vistos.append(params)
        return [dict(last=NOW, h=1.0)]
    monkeypatch.setattr(health, "query", q)
    assert health.check_odds_freshness()[0]
    assert vistos[0] == ("propline",)


def test_bajas_sin_fuente_no_alarman_con_propline(monkeypatch):
    import qf.config as cfg
    monkeypatch.setattr(cfg, "settings", SimpleNamespace(results_provider="propline"))
    monkeypatch.setattr(health, "query", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debe consultar")))
    ok, msg = health.check_injuries_coverage()
    assert ok and "sin fuente" in msg
