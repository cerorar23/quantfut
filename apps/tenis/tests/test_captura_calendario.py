"""Contrato del evento de calendario y proveedor falso (interfaz sin implementación real)."""
from datetime import datetime, timezone, timedelta

import pytest
from pydantic import ValidationError

from tenis.captura.calendario import EventoCalendario, ProveedorFalso

INICIO = datetime(2026, 11, 10, 14, 0, tzinfo=timezone.utc)


def _datos(**cambios):
    base = {"evento_id": "e-1", "circuito": "atp", "torneo": "Paris", "ronda": "R32", "jugador_1_id": 1,
            "jugador_2_id": 2, "inicio_utc": INICIO, "estado": "programado"}
    base.update(cambios)
    return base


def test_evento_valido():
    e = EventoCalendario(**_datos())
    assert e.circuito == "atp" and e.inicio_utc.tzinfo is not None


@pytest.mark.parametrize("cambio", [
    {"extra": 1},
    {"inicio_utc": datetime(2026, 11, 10, 14, 0)},          # sin zona horaria
    {"jugador_2_id": 1},                                     # mismo jugador en ambos lados
    {"circuito": "itf"},
    {"estado": "pospuesto"},
    {"ronda": "r32"},
    {"jugador_1_id": 0},
    {"jugador_1_id": "1"},                                   # strict: no coacciona cadenas
])
def test_evento_absurdo_se_rechaza(cambio):
    with pytest.raises(ValidationError):
        EventoCalendario(**_datos(**cambio))


def test_evento_es_inmutable():
    e = EventoCalendario(**_datos())
    with pytest.raises(ValidationError):
        e.estado = "terminado"


def test_proveedor_falso_filtra_por_intervalo():
    dentro = EventoCalendario(**_datos())
    fuera = EventoCalendario(**_datos(evento_id="e-2", inicio_utc=INICIO + timedelta(days=3)))
    p = ProveedorFalso([dentro, fuera])
    assert p.eventos(INICIO - timedelta(hours=1), INICIO + timedelta(hours=1)) == [dentro]
    assert p.eventos(INICIO, INICIO) == []  # intervalo semiabierto: el inicio exacto cuenta, el fin no
