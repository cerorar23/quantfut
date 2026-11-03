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

