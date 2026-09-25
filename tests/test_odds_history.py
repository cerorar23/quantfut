"""
Cuotas históricas de The Odds API. Ningún test llama a la API: lo que se fija
es que no se paga dos veces, que el presupuesto y la reserva paran, y que el
formato largo sale igual que el del backtest de football-data.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from qf.eval.soft_vs_sharp import evaluate, select_best_of
from qf.ingest import odds_history as oh

UTC = timezone.utc


def test_temprano_es_el_snapshot_de_las_12_con_al_menos_24h():
    ko = datetime(2025, 10, 18, 1, 0, tzinfo=UTC)
    assert oh.early_snapshot_time(ko) == datetime(2025, 10, 16, 12, tzinfo=UTC)
    ko = datetime(2025, 10, 18, 20, 0, tzinfo=UTC)
    assert oh.early_snapshot_time(ko) == datetime(2025, 10, 17, 12, tzinfo=UTC)
    for h in range(24):
        ko = datetime(2025, 10, 18, h, 30, tzinfo=UTC)
        lead = ko - oh.early_snapshot_time(ko)
        assert timedelta(hours=24) <= lead < timedelta(hours=48)


def test_el_plan_comparte_snapshots():
    ko1 = datetime(2025, 10, 18, 1, 0, tzinfo=UTC)
    ko2 = datetime(2025, 10, 18, 3, 0, tzinfo=UTC)
    ev = {"a": {"kickoff": ko1}, "b": {"kickoff": ko1}, "c": {"kickoff": ko2}}
    p = oh.plan_snapshots(ev)
    assert len(p.early) == 1, "los tres empiezan entre 24 y 48 h tras el mismo mediodía"
    assert len(p.close) == 2, "dos horas de inicio distintas"


def test_presupuesto_y_reserva():
    b = oh.Budget(limit=1000, reserve=100, remaining=120)
    b.check(10)
    with pytest.raises(oh.BudgetExceeded, match="reserva"):
        b.check(30)
    b = oh.Budget(limit=25)
    b.record({"x-requests-last": "10", "x-requests-remaining": "900"})
    b.record({"x-requests-last": "10", "x-requests-remaining": "890"})
    assert (b.spent, b.remaining) == (20, 890)
    with pytest.raises(oh.BudgetExceeded, match="presupuesto"):
        b.check(10)


def _fake_http(llamadas):
    def get(url, params):
        llamadas.append(params["date"])
        return ({"timestamp": params["date"], "data": []},
                {"x-requests-last": "10", "x-requests-remaining": "5000"})
    return get


def test_lo_que_esta_en_cache_no_se_vuelve_a_pagar(tmp_path, monkeypatch):
    llamadas = []
    monkeypatch.setattr(oh, "_http_get", _fake_http(llamadas))
    b = oh.Budget(limit=100)
    t = datetime(2025, 10, 17, 12, tzinfo=UTC)
    for _ in range(3):
        oh._historical("odds", "soccer_x", t, b, 10, tmp_path, markets="h2h", regions="eu")
    assert len(llamadas) == 1 and b.spent == 10


def test_fetch_para_al_agotar_el_presupuesto(tmp_path, monkeypatch):
    llamadas = []
    monkeypatch.setattr(oh, "_http_get", _fake_http(llamadas))
    base = datetime(2025, 10, 17, 12, tzinfo=UTC)
    plan = oh.Plan(early=[base + timedelta(days=i) for i in range(3)])
    out = oh.fetch("soccer_x", plan, oh.Budget(limit=20), cache=tmp_path)
    assert out["snapshots"] == 2 and len(llamadas) == 2


# --- de snapshots a formato largo -------------------------------------------

KO = datetime(2025, 10, 18, 1, 0, tzinfo=UTC)


def _book(key, h, d, a, upd):
    return {"key": key, "markets": [{"key": "h2h", "last_update": upd, "outcomes": [
        {"name": "Puebla", "price": h}, {"name": "Tijuana", "price": a},
        {"name": "Draw", "price": d}]}]}


def _write(tmp_path, t, snap_time, books, eid="e1"):
    path = (tmp_path / "soccer_x" /
            f"odds_{t.strftime('%Y%m%dT%H%M')}_markets-h2h_regions-eu.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    ev = {"id": eid, "home_team": "Puebla", "away_team": "Tijuana",
          "commence_time": oh._ts(KO), "bookmakers": books}
    path.write_text(json.dumps({"timestamp": oh._ts(snap_time), "data": [ev]}))


def _escenario(tmp_path, close_snap=None, pin_early=(2.40, 3.30, 3.00)):
    te, tc = oh.early_snapshot_time(KO), oh.close_snapshot_time(KO)
    fresh_e, fresh_c = oh._ts(te - timedelta(minutes=2)), oh._ts(tc - timedelta(minutes=2))
    _write(tmp_path, te, te, [
        _book("pinnacle", *pin_early, fresh_e),
        _book("onexbet", 2.70, 3.10, 2.80, fresh_e),
        _book("williamhill", 2.30, 3.20, 2.90, fresh_e),
        _book("betfair_ex_eu", 2.90, 3.60, 3.30, fresh_e),
        _book("tipico_de", 3.50, 3.00, 2.50, oh._ts(te - timedelta(hours=5))),
    ])
    _write(tmp_path, tc, close_snap or tc, [_book("pinnacle", 2.20, 3.40, 3.30, fresh_c)])
    return {"e1": {"kickoff": KO}}


def test_formato_largo_excluye_exchanges_y_cuotas_caducadas(tmp_path):
    q = oh.build_quotes("soccer_x", "mx.liga_mx", _escenario(tmp_path), cache=tmp_path)
    assert set(q["book"]) == {"onexbet", "williamhill"}
    assert len(q) == 6
    fila = q[(q["book"] == "onexbet") & (q["selection"] == "home")].iloc[0]
    assert fila["price_early"] == 2.70 and fila["sharp_close_price"] == 2.20
    assert fila["p_fair_close"] > fila["p_fair_early"], "el cierre se acortó hacia el local"


def test_un_cierre_demasiado_viejo_no_es_un_cierre(tmp_path):
    ev = _escenario(tmp_path, close_snap=KO - timedelta(minutes=45))
    assert oh.build_quotes("soccer_x", "mx.liga_mx", ev, cache=tmp_path).empty


def test_se_evalua_sin_resultados(tmp_path):
    q = oh.build_quotes("soccer_x", "mx.liga_mx", _escenario(tmp_path), cache=tmp_path)
    r = evaluate(select_best_of(q, ["onexbet", "williamhill"], 0.0))
    assert r["n"] >= 1 and r["n_with_result"] == 0 and r["roi"] is None
    assert r["ev_close"] > r["edge_early"], "el local 2,70 temprano vale más al cierre"


def test_pinnacle_apartado_del_consenso_no_es_referencia(tmp_path):
    ev = _escenario(tmp_path, pin_early=(3.60, 3.30, 2.10))
    q = oh.build_quotes("soccer_x", "mx.liga_mx", ev, cache=tmp_path)
    assert select_best_of(q, ["onexbet", "williamhill"], 0.0).empty
