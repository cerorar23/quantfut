"""
Sombra del criterio de picks. Lo que fijan estos tests:
  - la liquidación usa el cierre SIN margen de Pinnacle y, sin cierre, no mide;
  - "publicables" es lo que se habría publicado: una por partido, la primera
    vez que hubo stake, y de esa pasada la de mayor edge esperado;
  - la puerta solo mira las publicables, no todas las ofertas;
  - la antelación se agrupa en tramos.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from qf.config import settings
from qf.model.devig import devig
from qf.publish import picks as pk
from qf.publish import shadow_sharp as ss

T0 = datetime(2026, 9, 24, 8, tzinfo=timezone.utc)
CLOSE = {("home", None): 2.00, ("draw", None): 3.40, ("away", None): 4.00}


def test_tramos_de_antelacion():
    assert ss.lead_bucket(3 * 60) == "0-6h"
    assert ss.lead_bucket(30 * 60) == "24-48h"
    assert ss.lead_bucket(80 * 60) == ">=72h"


def test_liquidacion_contra_el_cierre_sin_margen():
    cp, p, clv_pct, ev, beat, outcome, profit = ss.settle_row("home", 2.20, CLOSE, 2, 1)
    fair = float(devig([2.00, 3.40, 4.00], settings.devig_method)[0])
    assert p == pytest.approx(fair)
    assert ev == pytest.approx((2.20 * fair - 1) * 100)
    assert clv_pct == pytest.approx(10.0) and clv_pct > ev, "la cifra con margen infla"
    assert (outcome, profit) == ("win", pytest.approx(1.20))


def test_sin_cierre_no_hay_valor_esperado():
    *_, ev, beat, outcome, profit = ss.settle_row("away", 3.90, {}, 2, 1)
    assert ev is None and beat is None
    assert (outcome, profit) == ("loss", -1.0)


def test_filas_de_oferta_llevan_antelacion_y_stake():
    o = pk.Offer("1xbet", "home", 2.20, 0.48, 5.6, 0.72, "api_football",
                 T0 - timedelta(hours=1))
    m = {"match_id": "m1", "league_id": "us.mls", "kickoff_utc": T0 + timedelta(hours=29)}
    (row,) = ss.offer_rows([o], m, {"1xbet": 0.5})
    assert row[3] == "1xbet" and row[13] == "api_football"
    assert row[15] == 30 * 60
    assert row[11] > 0, "1xBet con edge esperado positivo tiene stake"
    assert row[-1] == 0.5 and row[-2] == round(row[11] * 0.5, 2), \
        "el publicado lleva el factor; stake_units (el de la puerta) no"


def test_casa_sin_factor_usa_el_de_las_no_medidas():
    o = pk.Offer("betano", "home", 2.20, 0.48, 5.6, 0.42, "api_football",
                 T0 - timedelta(hours=1))
    m = {"match_id": "m1", "league_id": "us.mls", "kickoff_utc": T0 + timedelta(hours=29)}
    (row,) = ss.offer_rows([o], m, {})
    assert row[-1] == round(pk.factor_sin_medir(), 4)


def _f(rows):
    base = {"league_id": "us.mls", "kickoff_utc": T0 + timedelta(days=1),
            "odds_source": "api_football", "raw_edge_pct": 4.0, "lead_minutes": 1800,
            "clv_pct": 5.0, "beat_close": True, "profit_units": 0.5}
    return pd.DataFrame([{**base, **r} for r in rows])


def test_publicable_es_la_primera_pasada_con_stake_y_la_mejor_de_ella():
    f = _f([
        {"match_id": "m1", "book": "william_hill", "stake_units": 0.0,
         "expected_edge_pct": 0.0, "decided_at": T0, "ev_close_pct": -1.0},
        {"match_id": "m1", "book": "1xbet", "stake_units": 0.8,
         "expected_edge_pct": 2.0, "decided_at": T0 + timedelta(hours=1), "ev_close_pct": 2.0},
        {"match_id": "m1", "book": "betano", "stake_units": 1.0,
         "expected_edge_pct": 3.0, "decided_at": T0 + timedelta(hours=1), "ev_close_pct": 3.0},
        {"match_id": "m1", "book": "1xbet", "stake_units": 2.0,
         "expected_edge_pct": 9.0, "decided_at": T0 + timedelta(hours=5), "ev_close_pct": 9.0},
        {"match_id": "m2", "book": "1xbet", "stake_units": 0.0,
         "expected_edge_pct": 0.0, "decided_at": T0, "ev_close_pct": 1.0},
    ])
    pub = ss.publishable(f)
    assert list(pub["match_id"]) == ["m1"], "m2 nunca tuvo stake: no se habría publicado"
    assert pub.iloc[0]["book"] == "betano", "primera pasada con stake, la de mayor edge"


def test_la_puerta_solo_ve_las_publicables():
    filas = []
    for i in range(400):
        filas.append({"match_id": f"m{i}", "book": "1xbet", "stake_units": 1.0,
                      "expected_edge_pct": 3.0, "decided_at": T0,
                      "ev_close_pct": -2.0, "league_id": f"L{i % 4}"})
        filas.append({"match_id": f"m{i}", "book": "william_hill", "stake_units": 0.0,
                      "expected_edge_pct": 0.0, "decided_at": T0,
                      "ev_close_pct": 8.0, "league_id": f"L{i % 4}"})
    rep = ss.summarize(_f(filas))
    assert rep["n_offers"] == 800 and rep["publishable"]["n"] == 400
    assert rep["publishable"]["ev_close"] == pytest.approx(-2.0)
    assert rep["gate"]["authorized"] is False


def test_sin_datos_la_puerta_no_autoriza():
    rep = ss.summarize(pd.DataFrame())
    assert rep["gate"]["authorized"] is False


def test_pendientes_aparecen_pero_no_cuentan_como_clv():
    f = _f([
        {"match_id": "m1", "book": "1xbet", "stake_units": 0.8,
         "expected_edge_pct": 2.0, "decided_at": T0, "ev_close_pct": None,
         "clv_pct": None, "beat_close": None, "profit_units": None},
        {"match_id": "m1", "book": "bet365", "stake_units": 0.8,
         "expected_edge_pct": 3.0, "decided_at": T0 + timedelta(hours=1),
         "ev_close_pct": 4.0},
        {"match_id": "m2", "book": "1xbet", "stake_units": 0.8,
         "expected_edge_pct": 2.0, "decided_at": T0, "ev_close_pct": -1.0},
    ])
    rep = ss.summarize(f)
    assert rep["n_offers"] == 3
    assert rep["publishable"]["n"] == 2
    assert rep["publishable"]["n_with_fair_close"] == 1
    assert rep["publishable"]["ev_close"] == pytest.approx(-1.0)
    assert rep["gate"]["authorized"] is False


def test_report_incluye_ofertas_antes_de_liquidarlas(monkeypatch):
    sql = []

    def rows(query):
        sql.append(query)
        return _f([{"match_id": "m1", "book": "1xbet", "stake_units": 0.8,
                    "expected_edge_pct": 2.0, "decided_at": T0,
                    "ev_close_pct": None, "clv_pct": None,
                    "beat_close": None, "profit_units": None}]).to_dict("records")

    monkeypatch.setattr(ss, "query", rows)
    rep = ss.report()
    assert "LEFT JOIN sharp_shadow_results" in sql[0]
    assert rep["n_offers"] == 1
    assert rep["publishable"]["n"] == 1
    assert rep["publishable"]["n_with_fair_close"] == 0
    assert rep["gate"]["authorized"] is False


def _audit_row(offer_id, match_id, league="us.mls", **changes):
    row = {"offer_id": offer_id, "match_id": match_id, "league_id": league,
           "kickoff_utc": T0 + timedelta(hours=24), "stake_units": 0.8,
           "expected_edge_pct": 2.0, "decided_at": T0,
           "match_status": "scheduled", "home_goals": None,
           "away_goals": None, "result_offer_id": None,
           "ev_close_pct": None, "complete_sharp_close": False}
    return {**row, **changes}


def test_auditoria_distingue_ofertas_y_primera_candidata_por_liga():
    rows = [
        _audit_row(1, "m1", stake_units=0.0, expected_edge_pct=9.0),
        _audit_row(2, "m1", expected_edge_pct=2.0),
        _audit_row(3, "m1", expected_edge_pct=3.0),
        _audit_row(4, "m2", "mx.liga_mx", match_status="finished",
                   home_goals=2, away_goals=1),
        _audit_row(5, "m3", "mx.liga_mx", result_offer_id=5,
                   ev_close_pct=None),
        _audit_row(6, "m4", "mx.liga_mx", result_offer_id=6,
                   ev_close_pct=2.0),
    ]
    audit = ss.audit_summary(rows, T0)
    assert audit["total"]["captured"] == 6
    assert audit["total"]["with_stake"] == 5
    assert audit["total"]["candidates"] == 4
    assert audit["by_league"]["us.mls"]["candidates"] == 1
    assert audit["by_league"]["us.mls"]["candidate_states"]["scheduled"] == 1
    assert audit["by_league"]["mx.liga_mx"]["candidate_states"]["awaiting_settlement"] == 1
    assert audit["by_league"]["mx.liga_mx"]["candidate_states"]["settled_no_close"] == 1
    assert audit["by_league"]["mx.liga_mx"]["candidate_states"]["settled_with_fair_close"] == 1


@pytest.mark.parametrize(("changes", "expected"), [
    ({"kickoff_utc": T0 - timedelta(hours=1)}, "awaiting_result"),
    ({"kickoff_utc": T0 - timedelta(hours=4)}, "result_overdue"),
    ({"match_status": "finished"}, "finished_no_score"),
    ({"match_status": "postponed"}, "postponed_or_other"),
    ({"result_offer_id": 1, "complete_sharp_close": True},
     "settled_incomplete_close"),
])
def test_auditoria_explica_por_que_no_hay_clv(changes, expected):
    audit = ss.audit_summary([_audit_row(1, "m1", **changes)], T0)
    assert audit["total"]["candidate_states"][expected] == 1


def test_auditoria_consulta_cierre_sharp_y_no_modifica_datos(monkeypatch):
    statements = []

    def rows(sql, params):
        statements.append((sql, params))
        return []

    monkeypatch.setattr(ss, "query", rows)
    audit = ss.audit(T0)
    assert audit["total"]["captured"] == 0
    assert "window_tag = 'close'" in statements[0][0]
    assert statements[0][1] == (settings.sharp_book, settings.sharp_book)
    assert statements[0][0].lstrip().startswith("WITH latest_close")


def test_la_sombra_mide_todas_las_casas_pero_la_puerta_solo_las_de_la_lista():
    snap = pk.Snapshot("the_odds_api", T0, {
        "pinnacle": {"home": 2.0, "draw": 3.5, "away": 4.0},
        "nordicbet": {"home": 2.3, "draw": 3.4, "away": 3.6},
        "coolbet": {"home": 2.3, "draw": 3.4, "away": 3.6},
        "betfair_ex_eu": {"home": 2.5, "draw": 3.4, "away": 3.6},
        "unibet_se": {"home": 2.0, "draw": 3.4, "away": 3.9},
    })
    assert set(ss.casas_medibles(snap)) == {"nordicbet", "coolbet", "unibet_se"}
    filas = [{"match_id": "m1", "book": "nordicbet", "stake_units": 1.0,
              "decided_at": T0, "expected_edge_pct": 9.0},
             {"match_id": "m1", "book": "coolbet", "stake_units": 0.5,
              "decided_at": T0 + timedelta(hours=1), "expected_edge_pct": 2.0},
             {"match_id": "m2", "book": "nordicbet", "stake_units": 1.0,
              "decided_at": T0, "expected_edge_pct": 9.0}]
    pub = ss.publishable(pd.DataFrame(filas))
    assert list(pub["book"]) == ["coolbet"], "una casa fuera de la lista no abre la puerta"


def test_nunca_se_toma_una_oferta_del_snapshot_de_cierre(monkeypatch):
    ko = T0 + timedelta(minutes=10)
    snap = pk.Snapshot("the_odds_api", T0, {
        "pinnacle": {"home": 2.0, "draw": 3.5, "away": 4.0},
        "coolbet": {"home": 2.4, "draw": 3.4, "away": 3.6},
        "unibet_se": {"home": 2.0, "draw": 3.4, "away": 3.9},
        "leovegas_se": {"home": 2.0, "draw": 3.4, "away": 3.9}})
    insertadas = []
    monkeypatch.setattr(ss, "query", lambda *a, **k: [
        {"match_id": "m1", "league_id": "us.mls", "kickoff_utc": ko}])
    monkeypatch.setattr(ss.pk, "_af_snapshot", lambda *a: None)
    monkeypatch.setattr(ss.pk, "persistencias", lambda: dict(ss.pk.PERSISTENCE))
    monkeypatch.setattr(ss.pk, "_odds_api_snapshot", lambda *a: snap)
    monkeypatch.setattr(ss, "executemany", lambda sql, rows: insertadas.extend(rows) or len(rows))
    assert ss.capture(T0)["snapshots"] == 0 and insertadas == []
    ko = T0 + timedelta(hours=3)
    monkeypatch.setattr(ss, "query", lambda *a, **k: [
        {"match_id": "m1", "league_id": "us.mls", "kickoff_utc": ko}])
    assert ss.capture(T0)["snapshots"] == 1 and insertadas
