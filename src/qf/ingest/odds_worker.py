"""
Captura de snapshots de cuotas. ESTE ES EL PROCESO MÁS URGENTE DEL SISTEMA.

Cada día que este cron no corre es un día de datos que no se recupera y que
después no se puede comprar por menos de cuatro cifras. Ponlo en marcha antes
de escribir una sola línea de modelo.

Estrategia de ahorro de cuota: corre cada 10 minutos, pero solo llama a la API
cuando algún partido ENTRA en una ventana objetivo aún no capturada. Una
llamada devuelve todos los partidos de esa liga, así que el coste no crece con
el número de partidos, solo con el número de ligas x ventanas.

CONSUMO REAL (importante): The Odds API cobra en CRÉDITOS, no en llamadas.
Cada llamada cuesta n_mercados x n_regiones créditos.

    7 ligas x ~12 llamadas/semana x 4.3 semanas = ~360 llamadas/mes
    con regions=eu,us y markets=h2h,totals,spreads -> 6 créditos por llamada
    = ~2,160 créditos/mes

El plan gratuito da 500 créditos/mes, así que NO alcanza. Necesitas el plan de
$30/mes (20,000 créditos), que deja margen de sobra. Si quieres quedarte en el
gratuito para prototipar: usa regions=eu y markets=h2h (~360 créditos/mes),
pero pierdes el line shopping entre casas y los mercados derivados.

La región `eu` es la que trae Pinnacle y Betfair Exchange, que son la
referencia sharp de todo el sistema. Nunca la quites.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings
from ..db import copy_rows, execute, query, query_one
from ..normalize import resolve_team

log = logging.getLogger(__name__)

MARKET_MAP = {"h2h": "h2h", "totals": "totals", "spreads": "spreads"}


def _markets_for(sport_key: str) -> str:
    """
    Mercados que se pagan para esa competición. Cada mercado cuesta un crédito
    por llamada. En las ligas "solo sharp" (db/023) solo se paga el 1X2: es el
    único mercado del criterio, y el ensayo del 2026-09-25 no encontró valor
    en goles ni hándicap (0 de 1.448 precios). Desde db/052 lo decide
    `captura_completa`, no `model_enabled`: activar el modelo en una liga no
    triplica su gasto.
    """
    row = query_one("SELECT model_enabled, captura_completa FROM leagues "
                    "WHERE odds_api_key = %s LIMIT 1", (sport_key,))
    if row is not None and not (row["model_enabled"] and row["captura_completa"]):
        return "h2h"
    return settings.odds_api_markets


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=2, min=2, max=30))
def _fetch(sport_key: str, markets: str | None = None) -> tuple[list[dict], dict]:
    url = f"{settings.odds_api_base}/sports/{sport_key}/odds"
    params = {
        "apiKey": settings.odds_api_key,
        "regions": settings.odds_api_regions,
        "markets": markets or settings.odds_api_markets,
        "oddsFormat": "decimal",
        "dateFormat": "iso",
    }
    with httpx.Client(timeout=30) as c:
        r = c.get(url, params=params)
        r.raise_for_status()
        quota = {
            "remaining": r.headers.get("x-requests-remaining"),
            "used": r.headers.get("x-requests-used"),
        }
        return r.json(), quota


def _pending_windows(now: datetime, solo: tuple[str, ...] | None = None
                     ) -> dict[str, list[tuple[str, str]]]:
    """
    Devuelve {sport_key: [(match_id, window_tag), ...]} de partidos que están
    dentro de una ventana objetivo y aún no tienen captura para esa ventana.
    `solo` restringe las ventanas (la pasada de rescate del cierre).
    """
    rows = query(
        """
        SELECT m.match_id, l.odds_api_key,
               EXTRACT(EPOCH FROM (m.kickoff_utc - now())) / 60 AS mins,
               (SELECT count(DISTINCT lu.side) FROM lineups lu
                WHERE lu.match_id=m.match_id) AS lineup_sides,
               (SELECT max(lu.captured_at) FROM lineups lu
                WHERE lu.match_id=m.match_id) AS lineup_as_of
        FROM matches m
        JOIN leagues l ON l.league_id = m.league_id
        WHERE m.status = 'scheduled'
          AND l.odds_api_key IS NOT NULL
          AND l.active
          AND m.kickoff_utc BETWEEN now() - interval '10 minutes'
                                AND now() + interval '80 hours'
        """
    )
    captured = {
        (r["match_id"], r["window_tag"])
        for r in query("SELECT match_id, window_tag FROM odds_capture_log")
    }

    out: dict[str, list[tuple[str, str]]] = {}
    for r in rows:
        mins = float(r["mins"])
        for tag, hi, lo in settings.odds_windows:
            if solo is not None and tag not in solo:
                continue
            # Solo pagar otra captura cuando ambos XI ya son conocidos. La
            # cuota debe ser posterior al último XI y anterior al cierre.
            if tag == "post_xi" and (
                int(r.get("lineup_sides") or 0) < 2
                or r.get("lineup_as_of") is None
                or now <= r["lineup_as_of"]
            ):
                continue
            if lo <= mins <= hi and (r["match_id"], tag) not in captured:
                out.setdefault(r["odds_api_key"], []).append((r["match_id"], tag))
                break
    return out


def last_update(mk: dict, bk: dict) -> datetime | None:
    """
    Cuándo cambió por última vez el precio de esa casa en ese mercado. Es lo
    que permite medir la latencia de las casas blandas (db/038). Si el
    mercado no la trae se usa la de la casa, que es igual o más reciente.
    """
    raw = mk.get("last_update") or bk.get("last_update")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_event(ev: dict, match_id: str, window_tag: str,
                 now: datetime, kickoff: datetime) -> list[tuple]:
    mins_to_ko = int((kickoff - now).total_seconds() // 60)
    rows: list[tuple] = []
    home_name, away_name = ev.get("home_team"), ev.get("away_team")

    for bk in ev.get("bookmakers", []):
        book = bk["key"]
        for mk in bk.get("markets", []):
            mkey = MARKET_MAP.get(mk["key"])
            if not mkey:
                continue
            updated = last_update(mk, bk)
            for oc in mk.get("outcomes", []):
                name, price = oc.get("name"), oc.get("price")
                point = oc.get("point")
                if price is None or price <= 1.0:
                    continue

                if mkey == "h2h":
                    sel = ("home" if name == home_name
                           else "away" if name == away_name
                           else "draw")
                elif mkey == "totals":
                    sel = name.lower()          # 'over' | 'under'
                else:                            # spreads
                    sel = "home" if name == home_name else "away"

                rows.append((match_id, book, mkey, sel, point, float(price),
                             now, mins_to_ko, window_tag, "the_odds_api", updated))
    return rows


def match_meta(match_ids: list[str]) -> dict[str, dict]:
    return {
        r["match_id"]: r
        for r in query(
            """SELECT m.match_id, m.kickoff_utc, m.league_id,
                      th.canonical_name AS home, ta.canonical_name AS away
               FROM matches m
               JOIN teams th ON th.team_id = m.home_team_id
               JOIN teams ta ON ta.team_id = m.away_team_id
               WHERE m.match_id = ANY(%s)""",
            (list(match_ids),),
        )
    }


def match_events(events: list[dict], meta: dict[str, dict]) -> list[tuple[dict, str]]:
    """Empareja cada evento del feed con su partido de `meta` (nombres resueltos, ±2 h)."""
    # Un sport_key es una sola competición: la de cualquiera de sus partidos.
    seen_in = next(iter(meta.values()))["league_id"] if meta else None
    out = []
    for ev in events:
        ko = datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00"))
        home = resolve_team(ev.get("home_team", ""), "odds_api", seen_in=seen_in)
        away = resolve_team(ev.get("away_team", ""), "odds_api", seen_in=seen_in)
        if not home or not away:
            continue  # ya quedó registrado en unresolved_names

        match_id = None
        for mid, m in meta.items():
            if (m["home"] == home and m["away"] == away
                    and abs((m["kickoff_utc"] - ko).total_seconds()) < 7200):
                match_id = mid
                break
        if match_id is None:
            # No es un fallo: el feed trae TODOS los partidos de la
            # competición y `meta` solo los que tocan en esta ventana.
            # Como WARNING llenaba el log de ruido que nadie debe mirar.
            # Un nombre sin resolver sí es un problema y ya se registra
            # arriba en `unresolved_names`.
            log.debug("Evento fuera de ventana: %s vs %s",
                      ev.get("home_team"), ev.get("away_team"))
            continue
        out.append((ev, match_id))
    return out


def run_once(solo: tuple[str, ...] | None = None) -> dict:
    """
    Una pasada. Corre cada 10 minutos desde cron, y además una pasada de
    rescate SOLO del cierre desfasada 5 minutos (`--solo-cierre`): la ventana
    `close` (3-12 min) caía en una única pasada, y si fallaba la oferta se
    quedaba sin cierre justo para siempre. Con el rescate hay dos intentos;
    si el primero funcionó, el registro de captura hace que no gaste nada.
    """
    now = datetime.now(timezone.utc)
    pending = _pending_windows(now, solo)
    if not pending:
        return {"calls": 0, "rows": 0, "matches": 0}

    total_rows, total_matches, calls = 0, 0, 0
    quota: dict = {}

    for sport_key, targets in pending.items():
        try:
            events, quota = _fetch(sport_key, _markets_for(sport_key))
            calls += 1
        except Exception as exc:  # noqa: BLE001
            log.error("Fallo al consultar %s: %s", sport_key, exc)
            continue

        by_match = {mid: tag for mid, tag in targets}
        meta = match_meta(list(by_match))
        for ev, match_id in match_events(events, meta):
            tag = by_match[match_id]
            rows = _parse_event(ev, match_id, tag, now, meta[match_id]["kickoff_utc"])
            if not rows:
                continue

            copy_rows(
                "odds_snapshots",
                ["match_id", "bookmaker", "market", "selection", "line", "price",
                 "captured_at", "mins_to_kickoff", "window_tag", "source",
                 "book_updated_at"],
                rows,
            )
            execute(
                """INSERT INTO odds_capture_log (match_id, window_tag, rows_written)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (match_id, window_tag) DO NOTHING""",
                (match_id, tag, len(rows)),
            )
            total_rows += len(rows)
            total_matches += 1

    result = {"calls": calls, "rows": total_rows, "matches": total_matches,
              "quota_remaining": quota.get("remaining")}

    # Vigilancia de cuota: cuando se agota, la API devuelve 401/429 y el feed
    # se corta sin aviso a mitad de mes. Avisar con margen, no cuando ya pasó.
    rem = quota.get("remaining")
    if rem is not None:
        try:
            if int(rem) < 2000:
                from ..publish.telegram import alert
                alert(f"The Odds API: quedan {rem} créditos este mes. "
                      "Al llegar a cero la captura se detiene sin error.")
        except (TypeError, ValueError):
            pass

    from .api_football import record_health
    record_health("odds", total_rows, calls > 0 or not pending, result)
    log.info("Captura de cuotas: %s", result)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    import sys
    print(run_once(("close",) if "--solo-cierre" in sys.argv[1:] else None))
