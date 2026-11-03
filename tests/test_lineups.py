"""Disponibilidad de titulares (`lineups.availability`): historia en vivo e histórica."""
from __future__ import annotations

from qf.ingest import lineups


# --- availability(): historia en vivo + lineups_historicas (2026-10-02) ------
# Decisión del usuario: la historia de cada equipo (sus XI anteriores) puede
# salir también de `lineups_historicas`, igual que en el entrenamiento. El XI
# de HOY sigue saliendo solo de `lineups`, capturado antes del inicio.

def _xi(ids: range) -> list[dict]:
    return [{"player_id": i, "pos": "G" if i % 11 == 0 else "M"} for i in ids]


def _availability(monkeypatch, historia: list[dict]) -> tuple[dict, list[str]]:
    sqls = []

    def query(sql, params=None):
        sqls.append(sql)
        if "WHERE l.match_id = %s" in sql:
            return [{"side": "home", "starters": _xi(range(1, 12)),
                     "home_team_id": 10, "away_team_id": 20}]
        return historia

    monkeypatch.setattr(lineups, "query", query)
    return lineups.availability("hoy"), sqls


def test_el_xi_de_hoy_solo_sale_de_la_captura_en_vivo(monkeypatch):
    _, sqls = _availability(monkeypatch, [])
    assert "lineups_historicas" not in sqls[0]


def test_la_historia_lee_tambien_lineups_historicas(monkeypatch):
    _, sqls = _availability(monkeypatch, [])
    hist = sqls[1]
    assert "lineups_historicas" in hist
    # Solo XI completos, como en el entrenamiento; y si un partido está en las
    # dos tablas, manda el capturado en vivo.
    assert "jsonb_array_length(h.starters) >= 11" in hist
    assert "ORDER BY m.match_id, x.prioridad" in hist
    # Nunca partidos posteriores al de hoy.
    assert "m.kickoff_utc < (SELECT kickoff_utc FROM matches" in hist


def test_con_historia_historica_ya_no_es_insuficiente(monkeypatch):
    historia = [{"starters": _xi(range(1, 12)), "historico": True}] * 2 + \
               [{"starters": _xi(range(2, 13)), "historico": False}]
    out, _ = _availability(monkeypatch, historia)
    assert out["home"]["n_history"] == 3
    assert out["home"]["n_history_historico"] == 2
    assert out["home"]["missing_regulars"] == 0
