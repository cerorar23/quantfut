"""Parley NBA por partido (fase 4): cuándo se arma, qué se revalida y cómo se evita duplicar.

Un parley de un solo partido combina patas del MISMO juego, o sea un same-game: solo es
ejecutable con distribución conjunta validada y la cuota real del paquete que ofrece la
casa (``parley_v2.same_game``). Sin eso se registra como ``solo_referencia``. El producto de
probabilidades marginales no se usa nunca: la correlación medida llega a 1,45-1,59 sobre él.

Este módulo es puro (sin base de datos ni red): el llamador entrega el sellado oficial del
pronóstico, la disponibilidad actual y las cuotas.

Calendario (decisión del usuario, 2026-11-06):
  ejecución = max(inicio − 60 min, hora de sellado del pronóstico)
  nunca se selecciona después de inicio − 30 min.
"""
from __future__ import annotations

import hashlib
import itertools
from dataclasses import dataclass
from datetime import datetime, timedelta

from . import parley_v2 as v2
from .escalera import Opcion

ANTELACION_EJECUCION = timedelta(minutes=60)
ANTELACION_LIMITE = timedelta(minutes=30)
ESTADOS_FUERA = {"out", "doubtful", "questionable", "inactive", "suspended"}   # no basta con «probable»
MAX_PATAS_SAME_GAME = 4


def momento_ejecucion(inicio: datetime, sellado: datetime) -> datetime:
    """max(inicio − 60 min, sellado del pronóstico)."""
    return max(inicio - ANTELACION_EJECUCION, sellado)


def limite_seleccion(inicio: datetime) -> datetime:
    return inicio - ANTELACION_LIMITE


def puede_ejecutarse(ahora: datetime, inicio: datetime, sellado: datetime | None) -> tuple[bool, str]:
    """(sí/no, motivo). Sin sellado oficial del pronóstico no se selecciona."""
    if sellado is None:
        return False, "esperando el sellado oficial del pronóstico NBA"
    if ahora >= limite_seleccion(inicio):
        return False, "pasó inicio − 30 min: no se selecciona"
    if ahora < momento_ejecucion(inicio, sellado):
        return False, "antes de max(inicio − 60 min, sellado)"
    return True, "en ventana"


def clave_idempotente(evento_id: str, estrategia: str = v2.ESTRATEGIA, version: str = v2.VERSION,
                      tipo: str = "same_game") -> str:
    """Una sola fila por partido, estrategia, versión y tipo: reintentos y recalculos no duplican."""
    return hashlib.sha256(f"{estrategia}|{version}|{tipo}|{evento_id}".encode()).hexdigest()


# ------------------------------------------------------------------ revalidación
@dataclass(frozen=True)
class Contexto:
    """Lo que se vuelve a leer justo antes de publicar."""
    inicio: datetime
    estado_jugadores: dict[str, str]          # player_id → estado oficial (out, doubtful, active…)
    cuotas: dict[tuple, float]                # clave de contrato (v2._clave) → cuota vigente
    titulares: dict[str, bool] | None = None  # player_id → titular confirmado (None: sin dato)
    minutos_esperados: dict[str, float] | None = None


def revalidar(legs: list[Opcion], inicio_original: datetime, ctx: Contexto, tolerancia_cuota: float = 0.05,
              minutos_minimos: float = 20.0) -> tuple[str, list[str]]:
    """('ok' | 'recalcular' | 'anular', motivos).

    * horario distinto al del cálculo → recalcular;
    * jugador de una pata fuera/dudoso, sin titularidad o con minutos esperados bajos → anular;
    * cuota que cayó más de la tolerancia (o desapareció) → recalcular.
    """
    motivos: list[str] = []
    estado = "ok"
    if ctx.inicio != inicio_original:
        return "recalcular", [f"cambió el horario: {inicio_original.isoformat()} → {ctx.inicio.isoformat()}"]
    for o in legs:
        jugador = getattr(o, "jugador", ())
        if jugador:
            pid = jugador[0]
            est = (ctx.estado_jugadores.get(pid) or "").lower()
            if not est:
                motivos.append(f"sin estado oficial de {jugador[1] or pid}")
                estado = "anular"
            elif est in ESTADOS_FUERA:
                motivos.append(f"{jugador[1] or pid}: {est}")
                estado = "anular"
            if ctx.titulares is not None and ctx.titulares.get(pid) is False:
                motivos.append(f"{jugador[1] or pid} no es titular")
                estado = "anular"
            if ctx.minutos_esperados is not None and ctx.minutos_esperados.get(pid, 0.0) < minutos_minimos:
                motivos.append(f"{jugador[1] or pid}: minutos esperados bajos")
                estado = "anular"
        vigente = ctx.cuotas.get(v2._clave(o))
        if vigente is None:
            motivos.append(f"sin cuota vigente para {o.cand.market} {o.cand.selection}")
            estado = estado if estado == "anular" else "recalcular"
        elif vigente < o.price * (1 - tolerancia_cuota):
            motivos.append(f"la cuota cayó de {o.price:g} a {vigente:g}")
            estado = estado if estado == "anular" else "recalcular"
    return estado, motivos or ["sin cambios relevantes"]


# ------------------------------------------------------------------ parley de un partido
def _incompatibles(a: Opcion, b: Opcion) -> bool:
    """Patas que no pueden ir juntas: lados opuestos del mismo contrato o dos props del mismo jugador y mercado."""
    ja, jb = getattr(a, "jugador", ()), getattr(b, "jugador", ())
    if a.cand.market == b.cand.market and (ja[:1] == jb[:1]):
        return True
    return False


def parley_partido(opciones: list[Opcion], evento_id: str, cuota_paquete: float | None = None,
                   prob_conjunta: float | None = None, n_patas: int = 2) -> v2.Ticket | None:
    """El parley de un partido NBA: las patas elegidas por el selector v2 tratando cada pata como evento
    propio y envueltas como same-game. Sin cuota de paquete y modelo conjunto: ``solo_referencia``.

    Devuelve None si no hay ``n_patas`` compatibles con la política de cuotas.
    """
    if not 2 <= n_patas <= MAX_PATAS_SAME_GAME:
        raise ValueError("un same-game lleva entre 2 y 4 patas")
    base = [o for o in opciones if o.match_id == f"nba:{evento_id}" and v2.tope(o, 1) is not None]
    mejor = None
    # Mayor probabilidad conjunta aproximada de combinaciones compatibles dentro del rango de cuota 1,20-1,80.
    candidatas = sorted((o for o in base if v2.LEG_FLOOR <= o.price <= v2.LOW_CAP), key=lambda o: -o.cand.prob)[:12]
    for combo in itertools.combinations(candidatas, n_patas):
        if any(_incompatibles(a, b) for a, b in itertools.combinations(combo, 2)):
            continue
        if len({v2._clave(o) for o in combo}) < n_patas:
            continue
        puntaje = sum(o.cand.prob for o in combo)
        if mejor is None or puntaje > mejor[0]:
            mejor = (puntaje, combo)
    if mejor is None:
        return None
    return v2.same_game(list(mejor[1]), cuota_paquete=cuota_paquete, prob_conjunta=prob_conjunta)
