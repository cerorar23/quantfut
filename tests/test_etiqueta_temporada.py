"""
La columna `season` de un partido no puede depender de la fuente que lo creó.

Hasta el 2026-09-25 el calendario de API-Football etiquetaba la temporada de
año natural como '2026' (Brasil, Argentina, MLS) y la de Liga MX como '2026A'
/ '2027C', mientras el histórico de football-data las etiqueta '2627'. Una
misma temporada quedaba partida en dos etiquetas según quién hubiera creado
cada partido. El modelo no la usa, pero sí la API y cualquier consulta "por
temporada". La regla: el calendario etiqueta como lo haría el histórico, que
es la fuente de la inmensa mayoría de las filas.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from qf.ingest.fixtures import _season_label
from qf.ingest.history_fd import season_labels_extra


def _ko(y, m, d):
    return datetime(y, m, d, 20, tzinfo=timezone.utc)


@pytest.mark.parametrize("estilo,ko,esperada", [
    ("european", _ko(2026, 9, 26), "2627"),
    ("european", _ko(2027, 3, 14), "2627"),
    ("apertura_clausura", _ko(2026, 9, 26), "2627"),   # Apertura 2026
    ("apertura_clausura", _ko(2027, 3, 14), "2627"),   # Clausura 2027
    ("calendar", _ko(2026, 9, 26), "2627"),
    ("calendar", _ko(2026, 3, 14), "2627"),
])
def test_misma_etiqueta_que_el_historico(estilo, ko, esperada):
    assert _season_label({"season_style": estilo}, ko) == esperada


def test_ano_natural_casa_con_la_etiqueta_del_csv_extra():
    """BRA.csv / ARG.csv / USA.csv escriben '2026': tiene que caer en '2627'."""
    etiqueta = _season_label({"season_style": "calendar"}, _ko(2026, 9, 26))
    assert "2026" in season_labels_extra(etiqueta)


def test_liga_mx_casa_con_la_etiqueta_del_csv_extra():
    """MEX.csv escribe '2026/2027' para el Apertura 2026 y el Clausura 2027."""
    for ko in (_ko(2026, 9, 26), _ko(2027, 3, 14)):
        etiqueta = _season_label({"season_style": "apertura_clausura"}, ko)
        assert "2026/2027" in season_labels_extra(etiqueta)
