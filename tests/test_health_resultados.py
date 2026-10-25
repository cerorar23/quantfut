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
    """Con PropLine las bajas y el once salen de SofaScore (db/087): se mide su cobertura."""
    import qf.config as cfg
    monkeypatch.setattr(cfg, "settings", SimpleNamespace(results_provider="propline"))
    fila = {"prox": 40, "prox_con": 35, "emp": 30, "emp_con": 24}
    monkeypatch.setattr(health, "query", lambda *a, **k: [fila])
    ok, msg = health.check_injuries_coverage()
    assert ok and "35 de 40" in msg and "24 de 30" in msg
    fila.update(emp_con=6)
    ok, msg = health.check_injuries_coverage()
    assert not ok and "6 de 30" in msg
    fila.update(prox=4, prox_con=0, emp=3, emp_con=0)          # día sin partidos: no alarma
    assert health.check_injuries_coverage()[0]


def test_el_xg_alarma_por_cobertura_aunque_el_ultimo_sea_reciente(monkeypatch):
    monkeypatch.setattr(health, "query", lambda *a, **k: [
        {"league_id": "us.mls", "n": 12, "con": 3}, {"league_id": "es.laliga", "n": 8, "con": 8},
        {"league_id": "eu.uel", "n": 2, "con": 0}])
    ok, msg = health.check_xg_coverage()
    assert not ok and "us.mls 3/12" in msg and "eu.uel" not in msg
    assert any(fn is health.check_xg_coverage for _, fn in health.CHECKS)


def test_los_cierres_alarman_si_faltan(monkeypatch):
    import qf.config as cfg
    monkeypatch.setattr(cfg, "settings", SimpleNamespace(sharp_book="pinnacle"))
    monkeypatch.setattr(health, "query", lambda *a, **k: [{"n": 60, "con_cierre": 0}])
    ok, msg = health.check_closing_coverage()
    assert not ok and "0 de 60" in msg
    monkeypatch.setattr(health, "query", lambda *a, **k: [{"n": 60, "con_cierre": 48}])
    assert health.check_closing_coverage()[0]
    monkeypatch.setattr(health, "query", lambda *a, **k: [{"n": 4, "con_cierre": 0}])
    assert health.check_closing_coverage()[0]


def test_frescura_de_cuotas_de_propline_alarma_a_las_6_h(monkeypatch):
    import qf.config as cfg
    monkeypatch.setattr(cfg, "settings", SimpleNamespace(odds_provider="propline"))
    monkeypatch.setattr(health, "query", lambda sql, params=(): [dict(last=NOW, h=7.0)])
    assert not health.check_odds_freshness()[0]
