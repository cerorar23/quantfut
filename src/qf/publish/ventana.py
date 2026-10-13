"""
Ventana del pronóstico diario (decisión del titular, 2026-10-13).

El pronóstico de cada partido se calcula el MISMO día, en la corrida diaria de las
03:00 hora de México (09:00 UTC). El calendario se ve 7 días, pero un partido solo
tiene probabilidad desde su corrida; antes, la app lo enseña con candado.

Un partido pertenece a la corrida de las 03:00 de su día de México. Excepción: los que
empiezan antes de las 03:00 + MARGEN (ligas europeas de madrugada) ya habrían empezado
o no darían tiempo a sellar, así que pertenecen a la corrida del día anterior.

México no tiene horario de verano desde octubre de 2022: UTC-6 fijo todo el año.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

MEXICO = timezone(timedelta(hours=-6))
HORA_CORRIDA = 3
# Antelación mínima entre la corrida y el inicio del partido para que entre en ella.
MARGEN = timedelta(minutes=60)


def _corrida(dia: datetime) -> datetime:
    """Corrida (03:00 de México) del día de México de `dia`."""
    local = dia.astimezone(MEXICO)
    return local.replace(hour=HORA_CORRIDA, minute=0, second=0, microsecond=0)


def desbloqueo(kickoff: datetime) -> datetime:
    """Momento (UTC) desde el que el partido tiene pronóstico."""
    corrida = _corrida(kickoff)
    if kickoff.astimezone(MEXICO) < corrida + MARGEN:
        corrida -= timedelta(days=1)
    return corrida.astimezone(timezone.utc)


def proxima_corrida(now: datetime) -> datetime:
    """Primera corrida estrictamente posterior a `now`."""
    corrida = _corrida(now)
    if corrida <= now.astimezone(MEXICO):
        corrida += timedelta(days=1)
    return corrida.astimezone(timezone.utc)


def fin_ventana(now: datetime, tope: timedelta | None = None) -> datetime:
    """
    Último inicio de partido (UTC) que entra en la corrida de `now`: los que
    empiezan antes de la próxima corrida + MARGEN. `tope` evita ampliar el horizonte
    propio de cada generador de pronósticos.
    """
    # Exclusivo: un partido que empieza justo en el margen ya es de la corrida siguiente.
    fin = proxima_corrida(now) + MARGEN - timedelta(microseconds=1)
    return min(fin, now + tope) if tope is not None else fin
