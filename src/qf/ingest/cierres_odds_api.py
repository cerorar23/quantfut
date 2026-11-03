"""Cierres de Pinnacle del histórico de The Odds API para partidos que no tienen uno (F2b).

Un cierre aquí es el snapshot de 5 minutos antes del inicio, con el precio de Pinnacle
actualizado en los últimos 30 minutos. Lo descargado se guarda en disco antes de tocar la
base: cada crédito gastado se puede reprocesar sin volver a pagar. `odds_snapshots` no
admite DELETE, así que la carga es un ensayo salvo que se pida `--aplicar`.
"""
from __future__ import annotations

import logging
import math
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from ..normalize import match_team
from . import odds_history as oh
from .cierres import insertar_cierre

log = logging.getLogger(__name__)

FUENTE = "the_odds_api_hist"
COSTO_SNAPSHOT = oh.odds_call_cost("h2h", "eu")


def terna_de_evento(ev: dict, snap_time: datetime, kickoff: datetime) -> dict | None:
    """Terna 1X2 de Pinnacle del evento si el snapshot es un cierre de verdad; si no, None."""
    if not kickoff - oh.CLOSE_MAX_AGE <= snap_time <= kickoff:
        return None
    nombres = {ev.get("home_team"): "home", ev.get("away_team"): "away", "Draw": "draw"}
    for bk in ev.get("bookmakers", []):
        if bk.get("key") != "pinnacle":
            continue
        for mk in bk.get("markets", []):
            if mk.get("key") != "h2h":
                continue
            raw = mk.get("last_update") or bk.get("last_update")
            if not raw:
                return None
            upd = oh._parse_ts(raw)
            if upd > snap_time or snap_time - upd > oh.CLOSE_MAX_AGE:
                return None
            q = {nombres[o["name"]]: float(o["price"]) for o in mk.get("outcomes", [])
                 if o.get("name") in nombres and o.get("price") is not None}
            if set(q) != {"home", "draw", "away"} or not all(math.isfinite(v) and v > 1.0 for v in q.values()):
                return None
            return {"price": q, "book_updated_at": upd, "captured_at": snap_time}
    return None


def emparejar_eventos(eventos: list[dict], candidatos: list[dict], resolver_id) -> list[tuple[dict, dict]]:
    """Cada evento del feed con su partido pendiente: ids de equipo y hora (±2 h)."""
    out = []
    for ev in eventos:
        ko = oh._parse_ts(ev["commence_time"])
        h, a = resolver_id(ev.get("home_team", "")), resolver_id(ev.get("away_team", ""))
        if h is None or a is None:
            continue
        for c in candidatos:
            if (c["home_team_id"] == h and c["away_team_id"] == a
                    and abs((c["kickoff_utc"] - ko).total_seconds()) < 7200):
                out.append((ev, c))
                break
    return out


def planificar(candidatos: list[dict]) -> list[dict]:
    """
    Snapshots a pedir, uno por (competición, hora de inicio al minuto). Primero las competiciones
    que más partidos cubren por snapshot (las copas), y dentro de cada una lo más reciente.
    """
    grupos: dict[tuple[str, datetime], list[dict]] = defaultdict(list)
    liga_de: dict[str, str] = {}
    for c in candidatos:
        t = oh.close_snapshot_time(c["kickoff_utc"]).replace(second=0, microsecond=0)
        grupos[(c["sport"], t)].append(c)
        liga_de[c["sport"]] = c["league_id"]
    por_deporte: dict[str, list[datetime]] = defaultdict(list)
    for sport, t in grupos:
        por_deporte[sport].append(t)
    rendimiento = {s: sum(len(grupos[(s, t)]) for t in ts) / len(ts) for s, ts in por_deporte.items()}
    orden = sorted(por_deporte, key=lambda s: (-rendimiento[s], s))
    return [{"sport": s, "league_id": liga_de[s], "t": t, "matches": grupos[(s, t)]}
            for s in orden for t in sorted(por_deporte[s], reverse=True)]


def costo(slots: list[dict]) -> int:
    return len(slots) * COSTO_SNAPSHOT


def descargar(slots: list[dict], budget: oh.Budget, cache: Path) -> dict:
    """Gasta créditos: un snapshot por slot, en orden, hasta agotar el presupuesto."""
    hechos, parada = 0, None
    try:
        for s in slots:
            oh._historical("odds", s["sport"], s["t"], budget, COSTO_SNAPSHOT, cache,
                           markets="h2h", regions="eu")
            hechos += 1
    except oh.BudgetExceeded as exc:
        parada = "presupuesto"
        log.warning("Parada tras %d de %d snapshots: %s", hechos, len(slots), exc)
    return {"snapshots": hechos, "planeados": len(slots), "creditos": budget.spent, "parada": parada}


_PENDIENTES = """
    SELECT m.match_id, m.league_id, l.odds_api_key AS sport, m.kickoff_utc, m.home_team_id, m.away_team_id
    FROM matches m JOIN leagues l USING (league_id)
    WHERE m.status = 'finished' AND m.kickoff_utc >= %s AND l.odds_api_key IS NOT NULL
      AND (NOT %s OR l.model_enabled) AND (%s::text[] IS NULL OR m.league_id = ANY(%s::text[]))
      AND NOT EXISTS (SELECT 1 FROM odds_snapshots o WHERE o.match_id = m.match_id
                      AND o.bookmaker = 'pinnacle' AND o.market = 'h2h' AND o.window_tag = 'close')
    ORDER BY m.kickoff_utc"""


def pendientes(c, ligas: list[str] | None, desde: str, solo_modeladas: bool = True) -> list[dict]:
    """Partidos terminados sin cierre de Pinnacle (los mismos que `insertar_cierre` aceptaría)."""
    return c.execute(_PENDIENTES, (desde, solo_modeladas, ligas, ligas)).fetchall()


def resolver_id(nombre: str) -> int | None:
    """team_id por coincidencia EXACTA con la tabla de alias de The Odds API; no escribe nada."""
    tid, _, score = match_team(nombre, "odds_api", None)
    return tid if tid and score >= 100.0 else None


def cargar(c, slots: list[dict], cache: Path, resolver, aplicar: bool) -> dict:
    """Lee lo ya descargado (no gasta créditos) y adjunta el cierre a los partidos pendientes."""
    r = {"slots": len(slots), "sin_snapshot": 0, "emparejados": 0, "partidos_sin_evento": 0,
         "sin_cierre_valido": 0, "a_insertar": 0, "insertadas": 0}
    for s in slots:
        snap = oh._load_snapshot(s["sport"], s["t"], cache, "h2h", "eu")
        if snap is None:
            r["sin_snapshot"] += 1
            continue
        pares = emparejar_eventos(list(snap["events"].values()), s["matches"], resolver)
        r["emparejados"] += len(pares)
        r["partidos_sin_evento"] += len(s["matches"]) - len(pares)
        for ev, cand in pares:
            t = terna_de_evento(ev, snap["time"], cand["kickoff_utc"])
            if t is None:
                r["sin_cierre_valido"] += 1
                continue
            r["a_insertar"] += 1
            if aplicar:
                r["insertadas"] += insertar_cierre(
                    c, cand["match_id"], cand["kickoff_utc"], t["price"], captured_at=t["captured_at"],
                    book_updated_at=t["book_updated_at"], source=FUENTE)
    return r


def saldo_actual() -> int:
    """Créditos que quedan. `/sports` no consume créditos."""
    import httpx

    from ..config import settings
    resp = httpx.get(f"{settings.odds_api_base}/sports", params={"apiKey": settings.odds_api_key}, timeout=30)
    resp.raise_for_status()
    return int(float(resp.headers["x-requests-remaining"]))


def main(argv=None) -> None:
    import argparse
    import json

    from ..config import settings
    from ..db import conn

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("accion", choices=["plan", "fetch", "cargar"])
    p.add_argument("--ligas", nargs="*", default=None)
    p.add_argument("--desde", default="2024-01-01")
    p.add_argument("--todas", action="store_true", help="incluye las ligas fuera del modelo")
    p.add_argument("--presupuesto", type=int, default=0, help="créditos máximos de ESTA ejecución (fetch)")
    p.add_argument("--reserva", type=int, default=3000, help="saldo que debe quedar en la cuenta (fetch)")
    p.add_argument("--aplicar", action="store_true", help="sin esto, cargar es un ensayo")
    p.add_argument("--cache", default=f"{settings.artifact_dir}/odds_hist")
    a = p.parse_args(argv)
    cache = Path(a.cache)
    with conn() as c:
        slots = planificar(pendientes(c, a.ligas, a.desde, solo_modeladas=not a.todas))
        if a.accion == "plan":
            por_liga: dict[str, list[int]] = {}
            for s in slots:
                x = por_liga.setdefault(s["league_id"], [0, 0])
                x[0] += len(s["matches"])
                x[1] += 1
            for liga, (n, k) in por_liga.items():
                print(f"{liga:20} partidos={n:5} snapshots={k:5} créditos={k * COSTO_SNAPSHOT}")
            print(f"TOTAL partidos={sum(x[0] for x in por_liga.values())} snapshots={len(slots)} "
                  f"créditos={costo(slots)}")
        elif a.accion == "fetch":
            if a.presupuesto <= 0:
                raise SystemExit("fetch gasta créditos: indica --presupuesto N")
            b = oh.Budget(limit=a.presupuesto, reserve=a.reserva, remaining=saldo_actual())
            print(json.dumps({**descargar(slots, b, cache), "saldo": b.remaining}))
        else:
            print(json.dumps(cargar(c, slots, cache, resolver_id, a.aplicar), indent=1))


if __name__ == "__main__":
    main()
