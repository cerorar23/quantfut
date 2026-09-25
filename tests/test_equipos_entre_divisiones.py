"""
Un club que cambia de división dentro del catálogo NO se da de alta dos veces.

Caso real (2026-09-25): al añadir LaLiga 2 y Serie B, la liga nueva empieza
sin equipos. `match_team` no encuentra a nadie en ella y `resolve_or_register`
crearía de nuevo a los descendidos de LaLiga y Serie A, que ya existen con su
historia bajo la liga de primera. Un club duplicado parte su historial en dos
sin dar ningún error.

Regla: antes de crear, coincidencia EXACTA (nombre canónico o cualquier alias)
en las demás ligas domésticas del mismo país. Un parecido dudoso allí queda
pendiente de revisión, nunca se acepta solo: el difuso entre ligas es justo
lo que ya contaminó alias una vez (ver test_resolve_exacto.py).
"""
from __future__ import annotations

import pytest

from qf import normalize


@pytest.fixture
def base(monkeypatch):
    estado = {"liga": {}, "hermanas": {}, "inserts": [], "alias": [], "pendientes": []}
    monkeypatch.setattr(normalize, "_alias_map", lambda source: {})
    monkeypatch.setattr(normalize, "_league_teams", lambda league_id: estado["liga"])
    monkeypatch.setattr(normalize, "_sibling_teams", lambda league_id: estado["hermanas"])
    monkeypatch.setattr(normalize, "execute",
                        lambda sql, params=None: estado["inserts"].append(params) or 1)
    monkeypatch.setattr(normalize, "query_one", lambda sql, params=None: {"team_id": 999})
    monkeypatch.setattr(normalize, "clear_cache", lambda: None)
    monkeypatch.setattr(normalize, "register_alias",
                        lambda raw, src, tid: estado["alias"].append((raw, src, tid)))
    monkeypatch.setattr(normalize, "_record_unresolved",
                        lambda raw, src, lg, cand, score: estado["pendientes"].append((raw, cand)))
    return estado


def test_un_descendido_se_reutiliza_no_se_duplica(base):
    base["hermanas"] = {"leganes": {10}, "las palmas": {11}}
    assert normalize.resolve_or_register("Leganes", "api_football", "es.laliga2") == 10
    assert base["inserts"] == [], "no se crea un segundo Leganés"
    assert base["alias"] == [("Leganes", "api_football", 10)]


def test_un_parecido_dudoso_en_la_otra_division_queda_pendiente(base):
    base["hermanas"] = {"real valladolid": {12}}
    assert normalize.resolve_or_register("Valladolid", "api_football", "es.laliga2") is None
    assert base["inserts"] == [] and base["alias"] == []
    assert base["pendientes"] == [("Valladolid", "real valladolid")]


def test_un_nombre_repetido_en_dos_clubes_no_se_elige_a_ciegas(base):
    base["hermanas"] = {"racing": {21, 22}}
    assert normalize.resolve_or_register("Racing", "api_football", "es.laliga2") is None
    assert base["inserts"] == [] and base["pendientes"]


def test_un_club_nuevo_de_verdad_se_crea(base):
    base["hermanas"] = {"leganes": {10}}
    assert normalize.resolve_or_register("Cultural Leonesa", "api_football", "es.laliga2") == 999
    assert len(base["inserts"]) == 1


def test_sin_otras_divisiones_se_comporta_como_antes(base):
    assert normalize.resolve_or_register("Club Nuevo FC", "api_football", "us.mls") == 999
    assert len(base["inserts"]) == 1


def test_la_propia_liga_sigue_mandando(base):
    base["liga"] = {"leganes": 5}
    base["hermanas"] = {"leganes": {10}}
    assert normalize.resolve_or_register("Leganes", "api_football", "es.laliga2") == 5
