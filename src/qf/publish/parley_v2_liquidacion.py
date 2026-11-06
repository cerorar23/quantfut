"""Liquidación de las patas y tickets del parley v2 (fútbol, tenis y NBA).

* Fútbol: las mismas reglas que el parley actual (``escalera_datos.resultado`` contra la hora ORIGINAL
  del partido, nulo a las 48 h si no se jugó).
* Tenis y NBA: la calificación de PropLine (``resolution``) para la casa de la pata; si esa casa no la
  trae, la mayoría de las demás casas; sin acuerdo no se liquida. Pasadas ``MARGEN_SIN_RESULTADO`` desde
  el inicio sin calificación, la pata se anula (``void``), como hace la escalera.
* Un ticket se liquida cuando todas sus patas están liquidadas: pierde con una pata perdida; las
  devueltas (push/void) pagan a cuota 1.

Las filas inmutables las escribe esta función; el resolutor de PropLine es puro y se prueba aparte.
"""
from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Callable

from ..config import settings
from ..db import execute, query
from . import parley as pl
from . import picks as pk

log = logging.getLogger(__name__)

MARGEN_SIN_RESULTADO = timedelta(hours=72)
RESOLUCION = {"won": "win", "win": "win", "lost": "loss", "loss": "loss", "push": "push", "void": "void",
              "cancelled": "void", "refund": "void"}
_CLAVE_PROPLINE = {"h2h": "h2h", "spreads": "spreads", "handicap_games": "spreads", "totals": "totals",
                   "total_games": "totals"}


def _igual(a, b) -> bool:
    try:
        return abs(float(a) - float(b)) < 1e-9
    except (TypeError, ValueError):
        return False


def resolver_propline(pata: dict, filas: list[dict]) -> str | None:
    """win / loss / push / void de una pata de tenis o NBA, o None si aún no hay calificación.

    ``pata``: mercado, seleccion, linea, jugador_id, casa y evento (id, sport_key, inicio, local, visitante).
    """
    mercado = pata["mercado"]
    clave = _CLAVE_PROPLINE.get(mercado, mercado)
    evento = pata.get("evento") or []
    local, visitante = (evento[3], evento[4]) if len(evento) >= 5 else (None, None)
    lado = {"home": local, "away": visitante, "over": "Over", "under": "Under"}.get(pata["seleccion"])
    por_casa: dict[str, str] = {}
    for f in filas or []:
        if f.get("market") != clave or f.get("period") is not None or f.get("team") is not None:
            continue
        if f.get("name") != lado or f.get("resolution") is None:
            continue
        if clave == "h2h" and f.get("point") is not None:
            continue
        if clave != "h2h" and not _igual(f.get("point"), pata["linea"]):
            continue
        if pata.get("jugador_id") and str(f.get("player_id")) != str(pata["jugador_id"]):
            continue
        res = RESOLUCION.get(str(f["resolution"]).lower())
        if res:
            por_casa.setdefault(pk.canonical_book(f["bookmaker"]), res)
    propia = por_casa.get(pk.canonical_book(pata["casa"]))
    if propia:
        return propia
    cuentas = Counter(por_casa.values()).most_common(2)
    if cuentas and (len(cuentas) == 1 or cuentas[0][1] > cuentas[1][1]):
        return cuentas[0][0]
    return None


def resultado_pata(pata: dict, now: datetime, filas_propline: list[dict] | None = None,
                   fila_futbol: dict | None = None) -> tuple[str, float | None, str] | None:
    """(outcome, valor, fuente) o None si aún no se puede liquidar."""
    if pata["deporte"] == "futbol":
        from . import parley_datos as pd_
        if fila_futbol is None:
            return None
        res = pd_._resultado_pata(dict(fila_futbol, market=pata["mercado"], selection=pata["seleccion"],
                                       line=pata["linea"]), now)
        return None if res is None else (res[0], res[3], "matches")
    outcome = resolver_propline(pata, filas_propline or [])
    if outcome:
        return outcome, None, "propline"
    if pata["inicio_utc"] < now - MARGEN_SIN_RESULTADO:
        return "void", None, "sin_calificacion"
    return None


def liquidar_ticket(patas: list[tuple[str | None, float]]) -> dict | None:
    """[(outcome, cuota)] → {'outcome': ganado|perdido|nulo, 'factor_pago'} o None si falta una pata."""
    r = pl.liquidar([(o, p, 0.5) for o, p in patas])
    return None if r is None else {"outcome": r["outcome"], "factor_pago": r["factor_pago"]}


# ------------------------------------------------------------------ base de datos (se parchean en pruebas)
def _pendientes(now: datetime) -> list[dict]:
    return query(
        """SELECT p.pata_id, p.deporte, p.evento_id, p.mercado, p.seleccion, p.linea, p.jugador_id, p.book AS casa,
                  p.inicio_utc, p.evento,
                  m.status, m.kickoff_utc, p.inicio_utc AS kickoff_original, m.home_goals, m.away_goals,
                  m.home_corners, m.away_corners, m.home_yellow, m.away_yellow, m.home_red, m.away_red
           FROM parley_v2_patas p
           LEFT JOIN matches m ON p.deporte = 'futbol' AND m.match_id = p.evento_id
           LEFT JOIN parley_v2_resultados_pata r ON r.pata_id = p.pata_id
           WHERE r.pata_id IS NULL AND p.inicio_utc < %s""", (now,))


def _guardar_pata(pata_id, outcome: str, valor, fuente: str) -> int:
    return execute("""INSERT INTO parley_v2_resultados_pata (pata_id, outcome, valor, fuente)
                      VALUES (%s, %s, %s, %s) ON CONFLICT (pata_id) DO NOTHING""",
                   (pata_id, outcome, valor, fuente)) or 0


def _tickets_pendientes() -> list[dict]:
    return query(
        """SELECT t.ticket_id, p.price, rp.outcome
           FROM parley_v2_tickets t
           JOIN parley_v2_patas p ON p.ticket_id = t.ticket_id
           LEFT JOIN parley_v2_resultados_pata rp ON rp.pata_id = p.pata_id
           LEFT JOIN parley_v2_resultados r ON r.ticket_id = t.ticket_id
           WHERE r.ticket_id IS NULL ORDER BY t.ticket_id""")


def _guardar_ticket(ticket_id, outcome: str, factor: float) -> int:
    return execute("""INSERT INTO parley_v2_resultados (ticket_id, outcome, factor_pago)
                      VALUES (%s, %s, %s) ON CONFLICT (ticket_id) DO NOTHING""", (ticket_id, outcome, factor)) or 0


def leer_filas_propline(sport: str, evento_id: str, now: datetime) -> list[dict]:
    """Calificación de PropLine desde el archivo compartido (solo en una base con `read_results`)."""
    from ..ingest import propline_shared as ps
    if not hasattr(ps, "read_results"):
        raise RuntimeError("propline_shared de esta base no trae read_results")
    filas, _ = ps.read_results(settings.propline_archive, sport, evento_id, now)
    return filas or []


_SPORT = {"tenis": "tennis", "nba": "basketball_nba"}


def liquidar_pendientes(now: datetime | None = None,
                        leer_filas: Callable[[str, str, datetime], list[dict]] = leer_filas_propline) -> dict:
    """Liquida las patas con resultado y luego los tickets completos. Idempotente."""
    now = now or datetime.now(timezone.utc)
    n_patas = 0
    for r in _pendientes(now):
        pata = {"deporte": r["deporte"], "mercado": r["mercado"], "seleccion": r["seleccion"], "linea": r["linea"],
                "jugador_id": r["jugador_id"], "casa": r["casa"], "inicio_utc": r["inicio_utc"], "evento": r["evento"]}
        try:
            if r["deporte"] == "futbol":
                res = resultado_pata(pata, now, fila_futbol=r)
            else:
                res = resultado_pata(pata, now, filas_propline=leer_filas(_SPORT[r["deporte"]], r["evento_id"], now))
        except Exception:                      # un evento sin archivo no debe frenar a los demás
            log.exception("Parley v2: no se pudo liquidar la pata %s", r["pata_id"])
            continue
        if res is not None:
            n_patas += _guardar_pata(r["pata_id"], *res)
    por_ticket: dict = {}
    for f in _tickets_pendientes():
        por_ticket.setdefault(f["ticket_id"], []).append((f["outcome"], float(f["price"])))
    n_tickets = 0
    for ticket_id, patas in por_ticket.items():
        liq = liquidar_ticket(patas)
        if liq is not None:
            n_tickets += _guardar_ticket(ticket_id, liq["outcome"], liq["factor_pago"])
    return {"patas": n_patas, "tickets": n_tickets}


if __name__ == "__main__":                              # pragma: no cover - cron de producción
    import json
    print(json.dumps(liquidar_pendientes()))
