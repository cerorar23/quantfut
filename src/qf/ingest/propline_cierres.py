"""Cierres de PropLine (`/odds/closing`, ya archivados por el recolector compartido) a `odds_snapshots`.

Sin peticiones: el recolector pide el cierre de cada partido terminado y lo guarda con su recepción real.
Desde el 22-oct-2026 nada lo cargaba y CLV, sombra, puerta comercial y frescura del entrenamiento se quedaron sin
cierres (`docs/auditoria_datos_motores_20261025.md`).

Cada línea trae cuándo cambió por última vez (`closing_at`) y hasta cuándo se siguió viendo
(`closing_last_seen_at`). El de-vig del CLV exige un único `captured_at` por grupo, así que todas las líneas de un
partido se fechan en el último instante en que TODAS las usadas seguían a la vista; el precio de cada una es el mismo
en ese instante. Las que dejaron de verse más de `MAX_MIN_ANTES` minutos antes del inicio, o vienen `is_stale`, no
son cierre y no entran. Se carga después del partido: solo lo leen CLV, sombra y entrenamiento.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..config import settings
from ..db import conn, query
from .propline_ingest import ALIASES
from .propline_shared import SETTLEMENT_MAX_AGE, _fold, _same_club, decimal_price, newest, parse_time

log = logging.getLogger(__name__)

MAX_MIN_ANTES = 10
LOCK_ID = 61025091
TAG = "close"


def side_of(name, home, away):
    """'home' | 'away' | 'draw' para un nombre de la casa ("Ipswich Town" frente al evento "Ipswich"); None si duda."""
    if str(name or "").strip().lower() == "draw":
        return "draw"
    folded = _fold(name)
    hits = [s for s, team in (("home", home), ("away", away)) if _same_club(folded, _fold(team))]
    return hits[0] if len(hits) == 1 else None


def _team_of(market, home, away):
    """Lado del equipo de un mercado por equipo: `team` o el sufijo «… - Equipo» de la descripción."""
    team = market.get("team")
    if team is None and " - " in (market.get("description") or ""):
        team = market["description"].rsplit(" - ", 1)[1]
    return None if team is None else side_of(team, home, away)


def _selection(market, outcome, home, away):
    """(mercado, selección) con las claves de la captura horaria; None si no tiene equivalente."""
    key, name = market["key"], outcome.get("name")
    over_under = {"over": "over", "under": "under"}.get(str(name).lower())
    if key == "h2h" and market.get("team") is None:
        side = side_of(name, home, away)
        return (key, side) if side else None
    if key == "spreads" and market.get("team") is None:
        side = side_of(name, home, away)
        return (key, side) if side in ("home", "away") else None
    if key == "totals":
        if market.get("team") is None:
            return ("totals", over_under) if over_under else None
        side = _team_of(market, home, away)
        return ("team_totals_" + side, over_under) if side in ("home", "away") and over_under else None
    if key in ("total_corners", "total_cards") and market.get("team") is None:
        return ({"total_corners": "corners", "total_cards": "cards"}[key], over_under) if over_under else None
    if key == "team_corners":
        side = _team_of(market, home, away)
        return ("corners_" + side, over_under) if side in ("home", "away") and over_under else None
    if key == "both_teams_to_score":
        sel = {"yes": "yes", "no": "no"}.get(str(name).lower())
        return ("btts", sel) if sel else None
    if key == "double_chance":
        sides = {side_of(p, home, away) for p in str(name).replace(" or ", " Or ").split(" Or ")}
        combo = {frozenset({"home", "draw"}): "1X", frozenset({"draw", "away"}): "X2",
                 frozenset({"home", "away"}): "12"}.get(frozenset(sides))
        return ("double_chance", combo) if combo else None
    return None


def close_rows(doc, match_id, kickoff, books):
    """Filas de `odds_snapshots` de un cierre archivado; [] si no hay ninguna línea viva al inicio.

    `books` son las casas que se guardan (canónicas). Devuelve (filas, captured_at).
    """
    from ..publish.picks import canonical_book
    home, away = doc.get("home_team"), doc.get("away_team")
    vivas = []
    for b in doc.get("bookmakers", []):
        if canonical_book(b["key"]) not in books:
            continue
        for m in b.get("markets", []):
            if m.get("period") is not None:
                continue
            for o in m.get("outcomes", []):
                if o.get("is_stale") or not o.get("closing_last_seen_at") or o.get("redacted"):
                    continue
                visto = min(parse_time(o["closing_last_seen_at"]), kickoff)
                if (kickoff - visto) > timedelta(minutes=MAX_MIN_ANTES):
                    continue
                if o.get("closing_at") and parse_time(o["closing_at"]) > kickoff:
                    continue
                sel = _selection(m, o, home, away)
                if sel is None or (sel[0] not in ("h2h", "btts", "double_chance") and o.get("point") is None):
                    continue
                try:
                    price = decimal_price(o)
                except (KeyError, ValueError, TypeError):
                    continue
                vivas.append((b["key"], sel, o.get("point"), price, visto, o.get("book_updated_at")))
    if not vivas:
        return [], None
    at = min(v[4] for v in vivas)
    mins = int((kickoff - at).total_seconds() // 60)
    rows = [(match_id, book, market, sel, point, price, at, mins, TAG, "propline",
             parse_time(updated) if updated else None)
            for book, (market, sel), point, price, _, updated in vivas]
    return rows, at


def closing_events(root, sport):
    """Ids de evento con cierre archivado de ese deporte, según el índice del recolector (solo lectura)."""
    db_path = Path(root) / "index.sqlite"
    if not db_path.is_file():
        return []
    db = sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        rows = db.execute("""SELECT DISTINCT q.path FROM requests q JOIN receipts r ON r.request_id = q.id
                             WHERE q.path LIKE ? AND r.status = 200 AND r.error IS NULL""",
                          (f"/v1/sports/{sport}/events/%/odds/closing",)).fetchall()
    finally:
        db.close()
    return [p.split("/")[5] for (p,) in rows]


def pendientes(now, dias):
    """Partidos ya empezados de ligas activas sin cierre sharp ni registro de cierre, agrupados por deporte PropLine."""
    filas = query(
        """SELECT m.match_id, l.odds_api_key FROM matches m JOIN leagues l USING (league_id)
           WHERE l.active AND l.odds_api_key IS NOT NULL AND m.status <> 'postponed'
             AND m.kickoff_utc BETWEEN %s AND %s
             AND NOT EXISTS (SELECT 1 FROM odds_capture_log c WHERE c.match_id = m.match_id AND c.window_tag = %s)
             AND NOT EXISTS (SELECT 1 FROM odds_snapshots o WHERE o.match_id = m.match_id
                             AND o.window_tag = %s AND o.bookmaker = %s AND o.market = 'h2h')""",
        (now - timedelta(days=dias), now - timedelta(minutes=20), TAG, TAG, settings.sharp_book))
    out = {}
    for f in filas:
        out.setdefault(ALIASES.get(f["odds_api_key"], f["odds_api_key"]), []).append(f["match_id"])
    return out


def cargar(now=None, dias=45, dry_run=False):
    from ..publish.picks import canonical_book
    from .odds_worker import match_events, match_meta
    now = now or datetime.now(timezone.utc)
    root = settings.propline_archive
    books = {canonical_book(settings.sharp_book)} | {canonical_book(b) for b in settings.soft_books}
    r = dict(partidos=0, filas=0, sin_linea_viva=0, pendientes_sin_cierre=0, ligas={})
    with conn() as c:
        if not c.execute("SELECT pg_try_advisory_xact_lock(%s) AS ok", (LOCK_ID,)).fetchone()["ok"]:
            return {"skipped": "otra carga de cierres en marcha"}
        for sport, ids in pendientes(now, dias).items():
            meta = match_meta(ids)
            docs = []
            for ev in closing_events(root, sport):
                doc, rec = newest(root, f"/v1/sports/{sport}/events/{ev}/odds/closing", now,
                                  max_age_seconds=SETTLEMENT_MAX_AGE)
                if doc is None or not doc.get("commence_time"):
                    continue
                if parse_time(rec["received_at"]) < parse_time(doc["commence_time"]):
                    continue          # capturado antes del saque: no es un cierre
                docs.append(doc)
            pares = match_events([{"id": d["id"], "home_team": d["home_team"], "away_team": d["away_team"],
                                   "commence_time": d["commence_time"]} for d in docs], meta)
            por_id = {str(d["id"]): d for d in docs}
            emparejados = set()
            for ev, mid in pares:
                if mid in emparejados:
                    continue
                kickoff = meta[mid]["kickoff_utc"]
                doc = por_id[str(ev["id"])]
                if abs((parse_time(doc["commence_time"]) - kickoff).total_seconds()) > 900:
                    continue
                rows, _ = close_rows(doc, mid, kickoff, books)
                if not any(x[1] == settings.sharp_book and x[2] == "h2h" for x in rows):
                    r["sin_linea_viva"] += 1
                    continue
                emparejados.add(mid)
                r["partidos"] += 1
                r["filas"] += len(rows)
                liga = meta[mid]["league_id"]
                r["ligas"][liga] = r["ligas"].get(liga, 0) + 1
                if dry_run:
                    continue
                with c.cursor() as cur:
                    with cur.copy("""COPY odds_snapshots(match_id,bookmaker,market,selection,line,price,
                                  captured_at,mins_to_kickoff,window_tag,source,book_updated_at) FROM STDIN""") as s:
                        for row in rows:
                            s.write_row(row)
                c.execute("""INSERT INTO odds_capture_log(match_id,window_tag,rows_written) VALUES (%s,%s,%s)
                             ON CONFLICT(match_id,window_tag) DO NOTHING""", (mid, TAG, len(rows)))
            # Aún sin cierre archivado, sin emparejar o sin Pinnacle vivo: se reintenta en la próxima pasada.
            r["pendientes_sin_cierre"] += len(ids) - len(emparejados)
        if dry_run:
            c.rollback()
            return r
    if r["partidos"]:
        from ..eval.clv import settle_pending
        r["settled"] = settle_pending()
    from .api_football import record_health
    record_health("propline_cierres", r["filas"], True, {k: v for k, v in r.items() if k != "settled"})
    log.info("Cierres PropLine: %s", r)
    return r


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dias", type=int, default=45)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    print(json.dumps(cargar(dias=a.dias, dry_run=a.dry_run), default=str, ensure_ascii=False))
