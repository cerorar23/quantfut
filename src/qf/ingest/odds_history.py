"""
Cuotas HISTÓRICAS de The Odds API para validar el criterio "casa blanda contra
precio sharp" en las ligas que football-data no cubre antes del cierre (Liga
MX, Argentina, Brasil, MLS: su formato "extra" solo trae cierre).

Solo en planes de pago. Datos desde junio de 2020, snapshots cada 5 minutos
desde septiembre de 2022. Coste (medido el 2026-09-23): 1 crédito por llamada
de eventos, 10 × mercados × regiones por llamada de cuotas.

CÓMO SE GASTA LO MENOS POSIBLE
------------------------------
Un snapshot de cuotas devuelve TODOS los partidos próximos de la competición
(26 en Liga MX), así que:
  - precio TEMPRANO: un snapshot diario a las 12:00 UTC sirve a todos los
    partidos que empiezan entre 24 y 48 h después;
  - CIERRE: un snapshot por hora de inicio distinta, 5 min antes.
`plan` calcula el número exacto de llamadas ANTES de gastar, con el endpoint
de eventos (1 crédito cada semana de calendario).

POR QUÉ NO SE ESCRIBE EN `odds_snapshots`
-----------------------------------------
Esa tabla es inmutable: un error de parseo o de emparejamiento quedaría para
siempre y además alimenta el entrenamiento y la liquidación. Las respuestas se
guardan tal cual en disco (`.local/odds_hist/`): cada crédito gastado se puede
reprocesar sin volver a pagarlo, y cargarlas en la base es una decisión
aparte.

Solo 1X2 por defecto: el backtest de football-data no encontró oportunidades
verificables en over/under en casas reales, y cada mercado multiplica el coste.
"""
from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

from ..config import settings
from ..model.devig import devig

log = logging.getLogger(__name__)

CACHE = Path(".local/odds_hist")
EARLY_HOUR_UTC = 12
EARLY_MIN_LEAD = timedelta(hours=24)
CLOSE_LEAD = timedelta(minutes=5)
# Un "cierre" tomado más de esto antes del kickoff ya no es un cierre.
CLOSE_MAX_AGE = timedelta(minutes=30)
# Una cuota que la casa no actualiza desde hace más de esto no se trata como
# apostable: en el feed puede seguir apareciendo un precio que ya no existe.
QUOTE_MAX_AGE = timedelta(minutes=60)
# Exchanges: cobran comisión sobre la ganancia y su precio no es comparable
# con el de una casa. No entran como casa blanda.
EXCHANGES = {"betfair_ex_eu", "betfair_ex_uk", "betfair_ex_au", "matchbook",
             "smarkets"}
# Por debajo de este saldo no se hace ninguna llamada: es lo que necesita el
# worker en vivo hasta el reinicio mensual.
DEFAULT_RESERVE = 2000


def _ts(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def odds_call_cost(markets: str, regions: str) -> int:
    return 10 * len(markets.split(",")) * len(regions.split(","))


# --------------------------------------------------------------------------
# Presupuesto y llamadas
# --------------------------------------------------------------------------

class BudgetExceeded(RuntimeError):
    pass


@dataclass
class Budget:
    """
    Dos topes a la vez: lo que esta ejecución puede gastar (`limit`) y el saldo
    que tiene que quedar en la cuenta (`reserve`). El saldo real lo dice la
    cabecera `x-requests-remaining` de cada respuesta, no una cuenta local.
    """
    limit: int
    reserve: int = DEFAULT_RESERVE
    spent: int = 0
    remaining: int | None = None
    calls: int = 0

    def check(self, cost: int) -> None:
        if self.spent + cost > self.limit:
            raise BudgetExceeded(f"presupuesto de la ejecución agotado ({self.spent}/{self.limit})")
        if self.remaining is not None and self.remaining - cost < self.reserve:
            raise BudgetExceeded(f"saldo {self.remaining} no deja la reserva de {self.reserve}")

    def record(self, headers) -> None:
        self.calls += 1
        self.spent += int(headers.get("x-requests-last") or 0)
        rem = headers.get("x-requests-remaining")
        if rem is not None:
            self.remaining = int(float(rem))


def _http_get(url: str, params: dict):
    r = httpx.get(url, params=params, timeout=60)
    r.raise_for_status()
    return r.json(), r.headers


def _historical(kind: str, sport: str, date: datetime, budget: Budget,
                cost: int, cache: Path = CACHE, **extra) -> dict:
    """
    GET /historical/sports/{sport}/{kind} con caché en disco. Lo que ya está
    en caché no se vuelve a pagar nunca.
    """
    tag = "_".join(f"{k}-{v}" for k, v in sorted(extra.items()))
    path = cache / sport / f"{kind}_{date.strftime('%Y%m%dT%H%M')}{'_' + tag if tag else ''}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    budget.check(cost)
    data, headers = _http_get(
        f"{settings.odds_api_base}/historical/sports/{sport}/{kind}",
        {"apiKey": settings.odds_api_key, "date": _ts(date),
         "oddsFormat": "decimal", "dateFormat": "iso", **extra})
    budget.record(headers)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return data


# --------------------------------------------------------------------------
# Plan
# --------------------------------------------------------------------------

def discover_events(sport: str, start: datetime, end: datetime, budget: Budget,
                    step: timedelta = timedelta(days=7),
                    cache: Path = CACHE) -> dict[str, dict]:
    """
    Partidos de la competición entre `start` y `end`, con la hora de inicio de
    la ÚLTIMA vez que se vieron (los aplazamientos la cambian).
    """
    events: dict[str, dict] = {}
    t = start - timedelta(days=1)
    while t <= end:
        snap = _historical("events", sport, t, budget, cost=1, cache=cache)
        for ev in snap.get("data", []):
            ko = _parse_ts(ev["commence_time"])
            if start <= ko <= end:
                events[ev["id"]] = {**ev, "kickoff": ko}
        t += step
    return events


def early_snapshot_time(kickoff: datetime) -> datetime:
    """El snapshot diario de las 12:00 UTC más tardío que quede ≥24 h antes."""
    limit = kickoff - EARLY_MIN_LEAD
    t = limit.replace(hour=EARLY_HOUR_UTC, minute=0, second=0, microsecond=0)
    return t if t <= limit else t - timedelta(days=1)


def close_snapshot_time(kickoff: datetime) -> datetime:
    return kickoff - CLOSE_LEAD


@dataclass
class Plan:
    early: list[datetime] = field(default_factory=list)
    close: list[datetime] = field(default_factory=list)

    def calls(self) -> int:
        return len(self.early) + len(self.close)


def plan_snapshots(events: dict[str, dict]) -> Plan:
    kos = [e["kickoff"] for e in events.values()]
    return Plan(early=sorted({early_snapshot_time(k) for k in kos}),
                close=sorted({close_snapshot_time(k) for k in kos}))


def fetch(sport: str, plan: Plan, budget: Budget, markets: str = "h2h",
          regions: str = "eu", cache: Path = CACHE) -> dict:
    cost = odds_call_cost(markets, regions)
    done = 0
    try:
        for t in plan.early + plan.close:
            _historical("odds", sport, t, budget, cost, cache,
                        markets=markets, regions=regions)
            done += 1
    except BudgetExceeded as exc:
        log.warning("Parada por presupuesto tras %d de %d snapshots: %s",
                    done, plan.calls(), exc)
    return {"snapshots": done, "planned": plan.calls(), "credits_spent": budget.spent,
            "remaining": budget.remaining}


# --------------------------------------------------------------------------
# De snapshots a formato largo (el mismo que usa eval/soft_vs_sharp.py)
# --------------------------------------------------------------------------

def _h2h_prices(ev: dict, snap_time: datetime) -> dict[str, dict[str, float]]:
    """{casa: {home, draw, away}} con cuotas no caducadas y grupo completo."""
    names = {ev["home_team"]: "home", ev["away_team"]: "away", "Draw": "draw"}
    out = {}
    for bk in ev.get("bookmakers", []):
        for mk in bk.get("markets", []):
            if mk.get("key") != "h2h":
                continue
            upd = mk.get("last_update") or bk.get("last_update")
            if upd and snap_time - _parse_ts(upd) > QUOTE_MAX_AGE:
                continue
            q = {names[o["name"]]: float(o["price"]) for o in mk.get("outcomes", [])
                 if o.get("name") in names and o.get("price")}
            if set(q) == {"home", "draw", "away"} and min(q.values()) > 1.0:
                out[bk["key"]] = q
    return out


def _load_snapshot(sport: str, t: datetime, cache: Path, markets: str,
                   regions: str) -> dict | None:
    path = cache / sport / f"odds_{t.strftime('%Y%m%dT%H%M')}_markets-{markets}_regions-{regions}.json"
    if not path.exists():
        return None
    snap = json.loads(path.read_text(encoding="utf-8"))
    return {"time": _parse_ts(snap["timestamp"]),
            "events": {e["id"]: e for e in snap.get("data", [])}}


SEL = ("home", "draw", "away")


def build_quotes(sport: str, league_id: str, events: dict[str, dict],
                 cache: Path = CACHE, markets: str = "h2h",
                 regions: str = "eu") -> pd.DataFrame:
    """
    Una fila por (partido, selección, casa blanda) con los mismos campos que
    `soft_vs_sharp.build_quotes`. `won` queda vacío: The Odds API no da
    resultados históricos, y la vara de la puerta (valor esperado al cierre
    justo) no los necesita.
    """
    sharp = settings.sharp_book
    rows = []
    for eid, ev in events.items():
        ko = ev["kickoff"]
        early = _load_snapshot(sport, early_snapshot_time(ko), cache, markets, regions)
        close = _load_snapshot(sport, close_snapshot_time(ko), cache, markets, regions)
        if not early or not close or eid not in early["events"] or eid not in close["events"]:
            continue
        if ko - close["time"] > CLOSE_MAX_AGE:
            continue
        pe = _h2h_prices(early["events"][eid], early["time"])
        pc = _h2h_prices(close["events"][eid], close["time"])
        if sharp not in pe or sharp not in pc:
            continue
        fair_e = devig([pe[sharp][s] for s in SEL], settings.devig_method)
        fair_c = devig([pc[sharp][s] for s in SEL], settings.devig_method)
        soft = {b: q for b, q in pe.items() if b != sharp and b not in EXCHANGES}
        if not soft:
            continue
        consensus = np.mean([devig([q[s] for s in SEL], settings.devig_method)
                             for q in soft.values()], axis=0)
        dev = float(np.abs(consensus - fair_e).max())
        week = pd.Timestamp(ko).tz_convert(None).to_period("W")
        for j, s in enumerate(SEL):
            for book, q in soft.items():
                rows.append({"match": eid, "league_id": league_id, "week": str(week),
                             "market": "h2h", "selection": s, "book": book,
                             "price_early": q[s], "p_fair_early": float(fair_e[j]),
                             "p_fair_close": float(fair_c[j]),
                             "sharp_close_price": pc[sharp][s],
                             "sharp_dev_early": dev, "won": pd.NA})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _sport_of(league_id: str) -> str:
    from ..db import query_one
    row = query_one("SELECT odds_api_key FROM leagues WHERE league_id = %s", (league_id,))
    if not row or not row["odds_api_key"]:
        raise SystemExit(f"{league_id} no tiene odds_api_key")
    return row["odds_api_key"]


def main() -> None:
    ap = argparse.ArgumentParser(description="Cuotas históricas de The Odds API")
    ap.add_argument("accion", choices=["plan", "fetch", "report"])
    ap.add_argument("--league", required=True)
    ap.add_argument("--start", required=True, help="AAAA-MM-DD")
    ap.add_argument("--end", required=True, help="AAAA-MM-DD")
    ap.add_argument("--budget", type=int, default=0,
                    help="créditos máximos que esta ejecución puede gastar")
    ap.add_argument("--reserve", type=int, default=DEFAULT_RESERVE)
    ap.add_argument("--books", nargs="+", default=None,
                    help="lista blanca de casas para 'report' (claves de The Odds API)")
    a = ap.parse_args()

    start = datetime.fromisoformat(a.start).replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(a.end).replace(tzinfo=timezone.utc)
    sport = _sport_of(a.league)
    weeks = int((end - start).days / 7) + 2
    # `plan` puede gastar como mucho una llamada de eventos por semana.
    budget = Budget(limit=a.budget if a.accion == "fetch" else weeks, reserve=a.reserve)
    events = discover_events(sport, start, end, budget)
    plan = plan_snapshots(events)
    cost = odds_call_cost("h2h", "eu")
    print(f"{a.league}: {len(events)} partidos, {len(plan.early)} snapshots tempranos + "
          f"{len(plan.close)} de cierre = {plan.calls()} llamadas x {cost} = "
          f"{plan.calls() * cost} créditos (eventos: {budget.spent} gastados; "
          f"saldo {budget.remaining})")

    if a.accion == "fetch":
        print(fetch(sport, plan, budget))
    elif a.accion == "report":
        from ..eval.soft_vs_sharp import evaluate, select_best_of, select_by_book
        q = build_quotes(sport, a.league, events)
        if q.empty:
            print("Sin snapshots en caché para ese rango. Ejecuta fetch primero.")
            return
        print(f"partidos con temprano y cierre de Pinnacle: {q['match'].nunique()}")
        books = sorted(a.books or q["book"].unique())
        q = q[q["book"].isin(books)]
        for t in (0.0, 0.02, 0.04):
            r = evaluate(select_best_of(q, books, t))
            print(f"mejor de {len(books)} casas, umbral {t:.0%}: "
                  f"{ {k: r.get(k) for k in ('n', 'edge_early', 'ev_close', 'ev_close_ci95', 'persistence')} }")
        for b in books:
            r = evaluate(select_by_book(q, b, 0.02))
            if r["n"]:
                print(f"  {b:14s} 2%: n={r['n']:4d} ev={r['ev_close']} ci={r['ev_close_ci95']} "
                      f"pers={r['persistence']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    main()
