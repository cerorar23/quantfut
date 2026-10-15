"""Cierres de Pinnacle del histórico de The Odds API: solo se acepta un cierre de verdad."""
from datetime import datetime, timedelta, timezone

import pytest

from qf.ingest import cierres_odds_api as co
from qf.ingest import odds_history as oh

KO = datetime(2026, 4, 19, 14, 0, tzinfo=timezone.utc)


def _ev(precios=(1.9, 3.5, 4.2), upd="2026-04-19T13:54:40Z", libro="pinnacle", home="Local", away="Visita"):
    return {"id": "e1", "home_team": home, "away_team": away, "commence_time": "2026-04-19T14:00:00Z",
            "bookmakers": [{"key": libro, "last_update": upd, "markets": [{
                "key": "h2h", "last_update": upd, "outcomes": [
                    {"name": home, "price": precios[0]}, {"name": "Draw", "price": precios[1]},
                    {"name": away, "price": precios[2]}]}]}]}


def test_terna_valida_conserva_hora_de_captura_y_actualizacion():
    snap = KO - timedelta(minutes=5)
    t = co.terna_de_evento(_ev(), snap, KO)
    assert t["price"] == {"home": 1.9, "draw": 3.5, "away": 4.2}
    assert t["captured_at"] == snap and t["book_updated_at"] == datetime(2026, 4, 19, 13, 54, 40, tzinfo=timezone.utc)


@pytest.mark.parametrize("snap_min, upd", [
    (45, "2026-04-19T13:14:00Z"),      # snapshot a 45 min del inicio: ya no es un cierre
    (-3, "2026-04-19T13:54:40Z"),      # snapshot posterior al inicio
    (5, "2026-04-19T13:20:00Z"),       # el precio de Pinnacle tiene más de 30 min de antigüedad
    (5, "2026-04-19T14:30:00Z"),       # actualización posterior al snapshot: imposible
])
def test_terna_rechaza_cierres_que_no_lo_son(snap_min, upd):
    assert co.terna_de_evento(_ev(upd=upd), KO - timedelta(minutes=snap_min), KO) is None


def test_terna_rechaza_casa_ausente_cuota_invalida_o_terna_incompleta():
    snap = KO - timedelta(minutes=5)
    assert co.terna_de_evento(_ev(libro="bet365"), snap, KO) is None
    assert co.terna_de_evento(_ev(precios=(1.9, 1.0, 4.2)), snap, KO) is None
    ev = _ev()
    ev["bookmakers"][0]["markets"][0]["outcomes"].pop()
    assert co.terna_de_evento(ev, snap, KO) is None


def _cand(mid, liga, minutos, h=1, a=2, sport="soccer_x"):
    return {"match_id": mid, "league_id": liga, "sport": sport, "home_team_id": h, "away_team_id": a,
            "kickoff_utc": KO + timedelta(minutes=minutos)}


def test_emparejar_por_id_de_equipo_y_hora():
    cands = [_cand("m1", "L", 0, 1, 2), _cand("m2", "L", 0, 3, 4), _cand("m3", "L", 600, 1, 2)]
    ids = {"Local": 1, "Visita": 2, "Otro": 3, "Otro2": 4}
    eventos = [_ev(), _ev(home="Otro", away="Otro2"), _ev(home="Desconocido", away="Visita")]
    out = co.emparejar_eventos(eventos, cands, ids.get)
    assert [c["match_id"] for _, c in out] == ["m1", "m2"]       # m3 es el mismo cruce 10 h después


def test_planificar_agrupa_la_misma_hora_y_pone_primero_lo_barato():
    cands = [_cand("a1", "COPA", 0, sport="copa"), _cand("a2", "COPA", 0, sport="copa"),
             _cand("a3", "COPA", 0, sport="copa"), _cand("b1", "LIGA", 0, sport="liga"),
             _cand("b2", "LIGA", 180, sport="liga"), _cand("b3", "LIGA", 360, sport="liga")]
    slots = co.planificar(cands)
    assert [s["league_id"] for s in slots] == ["COPA", "LIGA", "LIGA", "LIGA"]
    assert len(slots[0]["matches"]) == 3 and slots[0]["t"] == KO - oh.CLOSE_LEAD
    assert [s["t"] for s in slots[1:]] == sorted((s["t"] for s in slots[1:]), reverse=True)   # lo reciente primero
    assert co.costo(slots) == 4 * 10


def test_descargar_para_al_agotar_el_presupuesto_y_no_repite_lo_ya_pagado(monkeypatch, tmp_path):
    cands = [_cand(f"m{i}", "L", 180 * i) for i in range(5)]
    slots = co.planificar(cands)
    llamadas = []

    def falsa(kind, sport, date, budget, cost, cache, **extra):
        budget.check(cost)
        llamadas.append(date)
        budget.spent += cost
        return {"timestamp": date.isoformat(), "data": []}

    monkeypatch.setattr(oh, "_historical", falsa)
    b = oh.Budget(limit=30, reserve=0)
    r = co.descargar(slots, b, tmp_path)
    assert r == {"snapshots": 3, "planeados": 5, "creditos": 30, "parada": "presupuesto"}
    assert len(llamadas) == 3
