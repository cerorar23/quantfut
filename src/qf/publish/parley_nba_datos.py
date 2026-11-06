"""Orquestación del parley NBA por partido (fase 4): ventana, revalidación y sellado.

Biblioteca sin cron propio: la dispara un revisor cada 5 minutos que conozca los partidos del día, su
hora de inicio, el sellado oficial del pronóstico NBA (v1.3, pendiente de programar) y la disponibilidad en
vivo. Aquí solo se decide y se sella; las fuentes llegan por parámetro.

Reglas (decisión del usuario, 2026-11-06): se ejecuta en ``max(inicio − 60 min, sellado)``, nunca después de
``inicio − 30 min``; antes de publicar se revalida horario, jugadores, titularidad, minutos y cuota
(recalcular una vez o anular); la clave es única por partido, estrategia y versión. Un parley de un partido
es un same-game: sin cuota real del paquete y modelo conjunto validado se sella como ``solo_referencia``.
Un ticket ya sellado no se modifica: si después deja de ser válido se anula con resultados ``void``.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable

from . import parley_nba as nba
from . import parley_v2 as v2
from . import parley_v2_datos as base
from .escalera import Opcion

log = logging.getLogger(__name__)
MAX_RECALCULOS = 1


def ejecutar_partido(now: datetime, evento_id: str, inicio: datetime, sellado: datetime | None,
                     cargar_ops: Callable[[datetime, str], list[Opcion]],
                     leer_contexto: Callable[[datetime, str], nba.Contexto],
                     cuota_paquete: float | None = None, prob_conjunta: float | None = None,
                     n_patas: int = 2, dry_run: bool = False) -> dict:
    """Un intento para un partido. Devuelve el estado: esperando, fuera_de_ventana, abstencion, anulado,
    ya_elegido o elegido."""
    if not base.habilitado() and not dry_run:
        return {"estado": "desactivado"}
    now = now.astimezone(timezone.utc)
    clave = nba.clave_idempotente(evento_id)
    lote_clave = f"{v2.ESTRATEGIA}|{v2.VERSION}|partido|{evento_id}"
    if not dry_run and base._existe(lote_clave):
        return {"estado": "ya_elegido", "evento_id": evento_id, "clave": clave}
    ok, motivo = nba.puede_ejecutarse(now, inicio, sellado)
    if not ok:
        fuera = now >= nba.limite_seleccion(inicio)
        return {"estado": "fuera_de_ventana" if fuera else "esperando", "motivo": motivo, "evento_id": evento_id}
    ticket, motivos = None, []
    for intento in range(MAX_RECALCULOS + 1):
        ops = cargar_ops(now, evento_id)
        ticket = nba.parley_partido(ops, evento_id, cuota_paquete, prob_conjunta, n_patas)
        if ticket is None:
            return {"estado": "abstencion", "motivo": "sin patas compatibles en rango", "evento_id": evento_id}
        veredicto, motivos = nba.revalidar(list(ticket.legs), inicio, leer_contexto(now, evento_id))
        if veredicto == "ok":
            break
        if veredicto == "anular" or intento == MAX_RECALCULOS:
            return {"estado": "anulado", "motivos": motivos, "evento_id": evento_id}
    resumen = {"estado": "elegido", "evento_id": evento_id, "tipo": ticket.tipo, "ticket_estado": ticket.estado,
               "patas": len(ticket.legs), "cuota_total": round(ticket.quote, 4), "motivos": list(ticket.motivos)}
    if dry_run:
        return resumen
    plan = v2.Plan((ticket,), (), {"revalidacion": motivos})
    br = base.Barrera(True, [], ("nba",), completa=True)
    lote = base.construir_lote(plan, now, inicio.astimezone(timezone.utc).date(), br, None, base._prev(),
                               ambito="partido", evento_id=evento_id)
    if not base._guardar(lote):
        return {"estado": "ya_elegido", "evento_id": evento_id, "clave": clave}
    log.info("Parley NBA sellado: %s", evento_id)
    return {**resumen, "chain": lote["chain_sha256"][:16]}


# ------------------------------------------------------------------ anulación de un ticket ya sellado
def _patas_del_ticket(ticket_id) -> list[dict]:
    from ..db import query
    return query("SELECT pata_id FROM parley_v2_patas WHERE ticket_id = %s", (ticket_id,))


def _anular(pata_id, fuente: str) -> int:
    from ..db import execute
    return execute("""INSERT INTO parley_v2_resultados_pata (pata_id, outcome, valor, fuente)
                      VALUES (%s, 'void', NULL, %s) ON CONFLICT (pata_id) DO NOTHING""", (pata_id, fuente)) or 0


def anular_publicado(ticket_id, motivos: list[str]) -> int:
    """Anula un ticket ya sellado sin modificarlo: sus patas quedan ``void`` y el ticket se liquida como nulo."""
    fuente = ("anulado: " + "; ".join(motivos))[:200]
    return sum(_anular(p["pata_id"], fuente) for p in _patas_del_ticket(ticket_id))
