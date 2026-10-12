"""
Captura de cuotas 1X2, goles y goles de cada equipo de API-Football: la fuente
de las casas donde apuestan los suscriptores (Bet365, Betano, 1xBet, William Hill),
con Pinnacle en la misma respuesta.

Consultado el 2026-09-23 (`/odds/bookmakers` y `/odds` por competición): de 33
casas del catálogo solo 9 cotizan nuestras competiciones, y esas 9 aparecen en
12 de 13. Betway, 888sport, Betcris y Sportingbet están en el catálogo con cero
partidos.

LÍMITES DEL PROVEEDOR, que condicionan cómo se usa
--------------------------------------------------
- Actualiza cada competición de golpe cada varias horas (medido: 2 h en MLS,
  19 h en Liga MX). No sirve como cierre: el cierre sigue saliendo de The Odds
  API. Sirve para DECIDIR con precios de 24-72 h antes.
- Solo guarda 7 días. Lo que no se capture a tiempo se pierde.
- Una sola marca `update` por partido para todas las casas: la casa blanda y
  Pinnacle de la misma respuesta tienen la misma antigüedad, que es lo que
  permite compararlas. Nunca comparar una casa de aquí con el Pinnacle de The
  Odds API: edades distintas fabrican ventajas falsas.
- No se sabe si su Bet365 o su Betano son el precio de la web mexicana o el
  internacional.

GOLES (2026-10-06): la misma petición trae "Goals Over/Under" (bet 5). Se
guardan todas las líneas de Pinnacle (el ajuste de goles de la línea de alta
probabilidad elige la que haya) y, de las casas de SOFT_BOOKS, solo
LINEAS_BLANDAS (cuota de referencia de los pronósticos de goles). Sin coste
extra: sigue siendo una petición por partido.

GOLES DE CADA EQUIPO (2026-10-07): bets 16 y 17 ("Total - Home" y "Total - Away"),
línea 0,5 de SOFT_BOOKS, para la cuota de referencia de la línea de alta probabilidad.

AMBOS ANOTAN, CÓRNERS Y TARJETAS (2026-10-08, escalera por probabilidad):
bets 8 ("Both Teams Score"), 45 ("Corners Over Under") y 80 ("Cards
Over/Under"), de SOFT_BOOKS y de Pinnacle (referencia). Mismo cuidado que en
16/17: id y nombre esperado, o no se guarda.

DOBLE OPORTUNIDAD (2026-10-12): bet 12 ("Double Chance"), de SOFT_BOOKS y de Pinnacle.
La nota anterior «ningún proveedor la cotiza» era falsa para API-Football (medido el
2026-10-12 en un partido de La Liga: 8 casas, incluidas Bet365, Betano, 1xBet y William
Hill). Los valores llegan como "Home/Draw", "Home/Away" y "Draw/Away" y se guardan como
'1X', '12' y 'X2' (los mismos nombres que `alta_prob.candidatos_doble`). Solo se guarda el
grupo completo de una casa. NO se sintetiza ninguna cuota: una cuota justa calculada desde
el 1X2 no la ofrece nadie y no sirve de precio de referencia.

Se guarda en `af_odds_snapshots`, no en `odds_snapshots` (ver db/016).
Una petición por partido dentro del horizonte.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

from ..config import settings
from ..db import executemany, query
from . import api_football as af

log = logging.getLogger(__name__)

HORIZON = timedelta(hours=72)
MATCH_WINNER = 1
SELECTIONS = {"Home": "home", "Draw": "draw", "Away": "away"}
GOALS_OU = 5
# De las casas blandas solo se guardan las líneas de la línea de alta
# probabilidad y la 2,5; de Pinnacle, todas.
LINEAS_BLANDAS = (1.5, 2.5, 3.5, 4.5)
# "Total - Home" (16) y "Total - Away" (17): solo para la cuota de referencia
# de "marca el local / el visitante" de la línea de alta probabilidad. El id
# solo no garantiza la semántica (el proveedor puede reasignar o añadir bets
# parecidos): se exige además el nombre esperado y, con otro, no se guarda nada.
TEAM_TOTALS = {16: ("Total - Home", "team_totals_home"),
               17: ("Total - Away", "team_totals_away")}
BTTS = (8, "Both Teams Score")
# Doble oportunidad: id, nombre esperado y cómo llegan los tres resultados.
DOBLE = (12, "Double Chance")
DOBLE_VALORES = {"Home/Draw": "1X", "Home/Away": "12", "Draw/Away": "X2"}
# Totales de córners y de tarjetas: id -> (nombre esperado, mercado). Córners
# de cada equipo (57/58) desde el 2026-10-09; ids comprobados en /odds/bets.
OTROS_TOTALES = {45: ("Corners Over Under", "corners"),
                 80: ("Cards Over/Under", "cards"),
                 57: ("Home Corners Over/Under", "corners_home"),
                 58: ("Away Corners Over/Under", "corners_away")}


def bookmaker_key(name: str) -> str:
    """'William Hill' -> 'william_hill', '1xBet' -> '1xbet'."""
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def _precio(v: dict) -> float | None:
    try:
        p = float(v.get("odd"))
    except (TypeError, ValueError):
        return None
    return p if p > 1.0 else None


def _totales(bet: dict) -> dict[float, dict[str, float]]:
    """
    {línea: {'over': cuota, 'under': cuota}}, solo pares completos y válidos.
    Un mismo (línea, lado) repetido invalida la línea entera: no se sabe cuál
    de las dos cuotas es la buena, y quedarse con la última dejaría un par
    incoherente (un over de una cotización con el under de otra).
    """
    out: dict[float, dict[str, float]] = {}
    vistos: set[tuple[float, str]] = set()
    repetidas: set[float] = set()
    for v in bet.get("values", []):
        partes = str(v.get("value", "")).split()
        if len(partes) != 2 or partes[0] not in ("Over", "Under"):
            continue
        try:
            linea = float(partes[1])
        except ValueError:
            continue
        lado = partes[0].lower()
        if (linea, lado) in vistos:
            repetidas.add(linea)
        vistos.add((linea, lado))
        p = _precio(v)
        if p is not None:
            out.setdefault(linea, {})[lado] = p
    return {ln: q for ln, q in out.items()
            if ln not in repetidas and set(q) == {"over", "under"}}


def parse(response: list[dict], match_id: str, kickoff: datetime) -> list[tuple]:
    """
    Filas para `af_odds_snapshots`. 1X2: solo casas con el grupo completo y
    cuotas válidas (un grupo incompleto no se puede de-vigar ni comparar).
    Goles (bet 5): pares over/under completos, todas las líneas de Pinnacle y
    LINEAS_BLANDAS de las casas de SOFT_BOOKS. Goles de cada equipo (bets 16/17):
    línea 0,5 de SOFT_BOOKS, para la cuota de referencia de la línea de alta
    probabilidad.
    """
    rows = []
    for item in response:
        updated = datetime.fromisoformat(item["update"])
        mins = int((kickoff - updated).total_seconds() // 60)
        fid = int(item["fixture"]["id"])
        for bk in item.get("bookmakers", []):
            if not bk.get("name"):
                continue
            book = bookmaker_key(bk["name"])
            for bet in bk.get("bets", []):
                if bet.get("id") == MATCH_WINNER:
                    q = {}
                    for v in bet.get("values", []):
                        sel, p = SELECTIONS.get(v.get("value")), _precio(v)
                        if sel and p is not None:
                            q[sel] = p
                    if set(q) == set(SELECTIONS.values()):
                        rows += [(match_id, fid, book, "h2h", s, p, updated, mins, None)
                                 for s, p in q.items()]
                elif bet.get("id") == GOALS_OU:
                    if book == settings.sharp_book:
                        lineas = None                    # todas
                    elif book in settings.soft_books:
                        lineas = LINEAS_BLANDAS
                    else:
                        continue
                    for ln, q in _totales(bet).items():
                        if lineas is None or ln in lineas:
                            rows += [(match_id, fid, book, "totals", s, p, updated, mins, ln)
                                     for s, p in q.items()]
                elif (bet.get("id"), bet.get("name")) == BTTS and (
                        book in settings.soft_books or book == settings.sharp_book):
                    q = {}
                    for v in bet.get("values", []):
                        sel, pr = {"Yes": "yes", "No": "no"}.get(v.get("value")), _precio(v)
                        if sel and pr is not None:
                            q[sel] = pr
                    if set(q) == {"yes", "no"}:
                        rows += [(match_id, fid, book, "btts", s, pr, updated, mins, None)
                                 for s, pr in q.items()]
                elif (bet.get("id"), bet.get("name")) == DOBLE and (
                        book in settings.soft_books or book == settings.sharp_book):
                    q = {}
                    for v in bet.get("values", []):
                        sel, pr = DOBLE_VALORES.get(v.get("value")), _precio(v)
                        if sel and pr is not None:
                            q[sel] = pr
                    if set(q) == set(DOBLE_VALORES.values()):
                        rows += [(match_id, fid, book, "double_chance", s, pr, updated, mins, None)
                                 for s, pr in q.items()]
                elif bet.get("id") in OTROS_TOTALES and (
                        book in settings.soft_books or book == settings.sharp_book):
                    nombre, mercado = OTROS_TOTALES[bet["id"]]
                    if bet.get("name") != nombre:
                        continue
                    for ln, q in _totales(bet).items():
                        rows += [(match_id, fid, book, mercado, s, pr, updated, mins, ln)
                                 for s, pr in q.items()]
                elif bet.get("id") in TEAM_TOTALS and book in settings.soft_books:
                    nombre, mercado = TEAM_TOTALS[bet["id"]]
                    q = _totales(bet).get(0.5) if bet.get("name") == nombre else None
                    if q:
                        rows += [(match_id, fid, book, mercado, s, p,
                                  updated, mins, 0.5) for s, p in q.items()]
    return rows


def _pending(now: datetime) -> list[dict]:
    return query(
        """SELECT m.match_id, m.kickoff_utc,
                  (m.external_ids ->> 'api_football')::int AS fixture_id
           FROM matches m
           JOIN leagues l ON l.league_id = m.league_id
           WHERE m.status = 'scheduled' AND l.active
             AND m.external_ids ? 'api_football'
             AND m.kickoff_utc BETWEEN %s AND %s
           ORDER BY m.kickoff_utc""",
        (now, now + HORIZON),
    )


def run_once() -> dict:
    now = datetime.now(timezone.utc)
    pending = _pending(now)
    calls = rows_new = with_odds = 0
    meta: dict = {}
    for m in pending:
        try:
            resp, meta = af.get("odds", {"fixture": m["fixture_id"]})
            calls += 1
        except af.PlanError:
            raise
        except Exception as exc:  # noqa: BLE001
            log.error("Cuotas de %s: %s", m["match_id"], exc)
            continue
        rows = parse(resp, m["match_id"], m["kickoff_utc"])
        if not rows:
            continue
        with_odds += 1
        rows_new += executemany(
            """INSERT INTO af_odds_snapshots
                 (match_id, af_fixture_id, bookmaker, market, selection, price,
                  provider_updated_at, mins_to_kickoff, line)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (match_id, bookmaker, market, selection, line,
                            provider_updated_at) DO NOTHING""",
            rows,
        )
    if meta:
        af.check_quota(meta)
    result = {"fixtures": len(pending), "calls": calls, "with_odds": with_odds,
              "rows_new": rows_new, "quota_remaining": meta.get("quota_remaining")}
    af.record_health("af_odds", rows_new, calls > 0 or not pending, result)
    log.info("Cuotas API-Football: %s", result)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    print(run_once())
