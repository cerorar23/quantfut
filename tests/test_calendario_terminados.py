"""
El calendario no reabre partidos terminados.

`fixtures` pide el día entero de hoy, así que los partidos que ya acabaron
llegan como FT. Antes de la guarda volvían a 'scheduled' y se borraba su
registro de captura de cuotas hasta que `results.py` los cerraba de nuevo.
"""
from __future__ import annotations

from datetime import datetime, timezone

from qf.ingest import fixtures

LIGA = {"league_id": "es.laliga2", "api_football_id": 141,
        "season_style": "european", "cross_league": False}
KO = datetime(2026, 9, 27, 12, tzinfo=timezone.utc)


def _preparar(monkeypatch, estado_en_base):
    ejecutados = []
    fx = {"fixture": {"id": 555, "date": KO.isoformat(), "status": {"short": "FT"}},
          "teams": {"home": {"name": "Valladolid"}, "away": {"name": "Cordoba"}}}
    monkeypatch.setattr(fixtures.af, "get", lambda *a, **k: ([fx], {"empty": False}))
    monkeypatch.setattr(fixtures.af, "check_quota", lambda meta: None)
    monkeypatch.setattr(fixtures, "_resolve", lambda league, name: 1 if name == "Valladolid" else 2)
    monkeypatch.setattr(fixtures, "query_one", lambda sql, params=(): {
        "match_id": "m", "kickoff_utc": KO, "status": estado_en_base})
    monkeypatch.setattr(fixtures, "execute", lambda sql, params=(): ejecutados.append(sql) or 1)
    return ejecutados


def test_un_partido_terminado_no_vuelve_a_programado(monkeypatch):
    ejecutados = _preparar(monkeypatch, "finished")
    r = fixtures.ingest_league(LIGA)
    assert ejecutados == [] and r["updated"] == 0


def test_uno_abierto_si_se_actualiza(monkeypatch):
    ejecutados = _preparar(monkeypatch, "postponed")
    assert fixtures.ingest_league(LIGA)["updated"] == 1
    assert any("UPDATE matches" in s for s in ejecutados)
