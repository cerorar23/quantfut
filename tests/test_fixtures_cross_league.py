"""
Verificación de la regla de resolución de equipos en competiciones de copa.

Es una regla de una línea con una consecuencia grande: en Champions y Europa
League NO se pueden dar de alta equipos. Si se dan de alta, el Real Madrid de
Champions pasa a ser un club distinto del de LaLiga, con una docena de
partidos y ningún rival en común, y a partir de ahí el modelo de fuerza
aprende basura sin que nada falle.

Aquí se prueba `_resolve` con la base de datos simulada, porque lo que se
puede romper en silencio es la DECISIÓN (crear vs no crear, difuso vs exacto),
no el SQL.
"""
from __future__ import annotations

import pytest

from qf.ingest import fixtures


@pytest.fixture
def espias(monkeypatch):
    """Sustituye las dos vías de resolución y anota cuál se usó."""
    registro = {"creados": [], "buscados": [], "sin_resolver": []}

    def fake_resolve_or_register(raw, source, league_id):
        registro["creados"].append((raw, league_id))
        return 999

    def fake_match_team(raw, source, league_id):
        registro["buscados"].append((raw, league_id))
        return fake_match_team.respuesta

    fake_match_team.respuesta = (None, None, 0.0)

    def fake_record(raw, source, league_id, cand, score):
        registro["sin_resolver"].append(raw)

    monkeypatch.setattr(fixtures, "resolve_or_register", fake_resolve_or_register)
    monkeypatch.setattr(fixtures, "match_team", fake_match_team)
    monkeypatch.setattr(fixtures, "_record_unresolved", fake_record)
    return registro, fake_match_team


LIGA = {"league_id": "es.laliga", "cross_league": False}
COPA = {"league_id": "eu.ucl", "cross_league": True}


def test_en_una_liga_normal_un_ascendido_se_da_de_alta(espias):
    registro, _ = espias
    assert fixtures._resolve(LIGA, "Equipo Recien Ascendido") == 999
    assert registro["creados"] == [("Equipo Recien Ascendido", "es.laliga")]
    assert registro["buscados"] == []


def test_en_copa_nunca_se_da_de_alta_un_equipo(espias):
    registro, fake = espias
    fake.respuesta = (None, "algun candidato", 0.0)
    assert fixtures._resolve(COPA, "Club Que No Tenemos") is None
    assert registro["creados"] == []          # <- lo que de verdad importa
    assert registro["sin_resolver"] == ["Club Que No Tenemos"]


def test_en_copa_se_busca_en_todo_el_catalogo_no_en_la_competicion(espias):
    """
    El equipo pertenece a su liga doméstica, no a 'eu.ucl'. Buscarlo dentro de
    la competición no lo encontraría nunca: ahí no hay ni un equipo.
    """
    registro, fake = espias
    fake.respuesta = (42, "real madrid", 100.0)
    assert fixtures._resolve(COPA, "Real Madrid") == 42
    assert registro["buscados"] == [("Real Madrid", None)]


def test_en_copa_una_coincidencia_difusa_se_rechaza(espias):
    """
    La protección clave. Con la búsqueda abierta a las 8 ligas, un difuso de 95
    puntos puede colocar un club europeo encima de uno latinoamericano de
    nombre parecido y contaminar dos historiales a la vez.
    """
    registro, fake = espias
    fake.respuesta = (7, "santos", 95.0)
    assert fixtures._resolve(COPA, "Santos") is None
    assert registro["sin_resolver"] == ["Santos"]


def test_en_liga_normal_el_difuso_si_vale(espias):
    """El umbral estricto es SOLO para copas; dentro de una liga no cambia nada."""
    registro, _ = espias
    fixtures._resolve(LIGA, "Ath Bilbao")
    assert registro["creados"] == [("Ath Bilbao", "es.laliga")]


def test_una_liga_sin_la_clave_cross_league_se_trata_como_normal(espias):
    """
    `cross_league` llega de la consulta. Si algún día alguien quita esa columna
    del SELECT, el comportamiento debe degradar a "liga normal", no reventar.
    """
    registro, _ = espias
    assert fixtures._resolve({"league_id": "es.laliga"}, "Getafe") == 999
    assert registro["creados"] == [("Getafe", "es.laliga")]
