"""
Los clubes de copa fuera del catálogo (Celtic, Salzburgo…) son irresolubles
por diseño: nunca se dan de alta bajo `eu.*`. `health.check_unresolved_names`
ya los cuenta como esperados; `fixtures.run()` los trataba como incidencia y,
con Telegram activo (2-oct-2026), habría avisado dos veces al día por algo
normal. Una incidencia de una liga doméstica sigue alertando.
"""
from __future__ import annotations

from qf.ingest import fixtures

LIGAS = [{"league_id": "eu.ucl", "cross_league": True},
         {"league_id": "es.laliga", "cross_league": False}]


def _run(monkeypatch, sin_emparejar: dict[str, int]) -> tuple[dict, list]:
    avisos = []
    monkeypatch.setattr(fixtures, "query", lambda sql, params=None: LIGAS)
    monkeypatch.setattr(fixtures, "ingest_league", lambda lg, days: {
        "league": lg["league_id"], "inserted": 0, "updated": 0, "duplicated": 0,
        "unresolved": sin_emparejar.get(lg["league_id"], 0), "empty": False})
    monkeypatch.setattr(fixtures, "record_health", lambda *a, **k: None)
    import qf.publish.telegram as tg
    monkeypatch.setattr(tg, "alert", avisos.append)
    return fixtures.run(), avisos


def test_clubes_de_copa_fuera_del_catalogo_no_alertan(monkeypatch):
    r, avisos = _run(monkeypatch, {"eu.ucl": 12})
    assert r["problems"] == [] and avisos == []
    assert any("eu.ucl" in n for n in r["notes"])


def test_un_equipo_sin_emparejar_en_liga_domestica_si_alerta(monkeypatch):
    r, avisos = _run(monkeypatch, {"es.laliga": 1, "eu.ucl": 12})
    assert r["problems"] == ["es.laliga: 1 equipos sin emparejar"]
    assert len(avisos) == 1 and "eu.ucl" not in avisos[0]
