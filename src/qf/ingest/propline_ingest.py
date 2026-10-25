"""Feed existing football consumers from the shared archive, with zero HTTP calls.

Hourly observations remain hourly: never manufacture close/post-XI timestamps.
The original archive preserves every other market for future adapters/training.
"""
from datetime import datetime, timezone

from ..config import settings
from ..db import query, conn
from .propline_shared import newest, football_feed, parse_time, quotes

ALIASES = {
    "soccer_epl": "soccer_epl", "soccer_england_efl_champ": "soccer_championship",
    "soccer_efl_champ": "soccer_championship",
    "soccer_spain_la_liga": "soccer_la_liga", "soccer_italy_serie_a": "soccer_serie_a",
    "soccer_germany_bundesliga": "soccer_bundesliga", "soccer_france_ligue_one": "soccer_ligue_1",
    "soccer_netherlands_eredivisie": "soccer_eredivisie", "soccer_portugal_primeira_liga": "soccer_primeira_liga",
    "soccer_mexico_ligamx": "soccer_liga_mx", "soccer_usa_mls": "soccer_mls",
    "soccer_brazil_campeonato": "soccer_brasileirao", "soccer_argentina_primera_division": "soccer_argentina_primera",
    "soccer_turkey_super_league": "soccer_turkey_super_lig", "soccer_germany_bundesliga2": "soccer_germany_bundesliga2",
    "soccer_switzerland_superleague": "soccer_swiss_super_league",
    "soccer_norway_eliteserien": "soccer_eliteserien",
    "soccer_uefa_champs_league": "soccer_uefa_champions_league",
    "soccer_uefa_europa_league": "soccer_uefa_europa_league",
}


def catalog_keys(now):
    """Claves de deporte del último catálogo `/v1/sports` archivado (hasta 3 días), o None si no hay."""
    sports, receipt = newest(settings.propline_archive, "/v1/sports", now, max_age_seconds=3 * 86400)
    if receipt is None:
        return None
    return {s.get("key") for s in sports}


def soft_allowed(observed, kickoff):
    """Casas que se guardan de esta observación: la sharp siempre; las demás cerca del inicio y cada pocas horas."""
    from ..publish.picks import canonical_book
    allowed = {canonical_book(settings.sharp_book)}
    near = (kickoff - observed).total_seconds() <= settings.propline_soft_horizon_hours * 3600
    if near and observed.hour % max(1, settings.propline_soft_every_hours) == 0:
        allowed |= {canonical_book(b) for b in settings.soft_books}
    return allowed


def football_rows(event, match_id, observed, kickoff, tag, allowed_books=None):
    from ..publish.picks import canonical_book
    rows = []
    for q in quotes([event], observed.isoformat()):
        if allowed_books is not None and canonical_book(q["bookmaker"]) not in allowed_books:
            continue
        if q["flags"] or q["period"] is not None:
            continue
        market, side = q["market"], q["side"]
        selection = None
        if market in ("h2h", "spreads") and q["team"] is None:
            if side in (("home", "away", "draw") if market == "h2h" else ("home", "away")):
                selection = side
        elif market in ("totals", "total_corners", "total_cards", "team_corners"):
            selection = {"Over": "over", "Under": "under"}.get(q["name"])
            if q["point"] is None:
                continue
            if market == "totals" and q["team"] is not None:
                team_side = "home" if q["team"] == event["home_team"] else "away" if q["team"] == event["away_team"] else None
                if team_side is None:
                    continue
                market = "team_totals_" + team_side
            elif market == "team_corners":
                team_side = "home" if q["team"] == event["home_team"] else "away" if q["team"] == event["away_team"] else None
                if team_side is None:
                    continue
                market = "corners_" + team_side
            elif q["team"] is not None:
                continue
            else:
                market = {"total_corners": "corners", "total_cards": "cards"}.get(market, market)
        elif market == "both_teams_to_score":
            market, selection = "btts", {"Yes": "yes", "No": "no"}.get(q["name"])
        elif market == "double_chance":
            selection = {"1X": "1X", "X2": "X2", "12": "12",
                event["home_team"] + " or Draw": "1X", "Draw or " + event["away_team"]: "X2",
                event["home_team"] + " or " + event["away_team"]: "12"}.get(q["name"])
        if selection is None:
            continue
        updated = parse_time(q["book_updated_at"]) if q["book_updated_at"] else None
        rows.append((match_id,q["bookmaker"],market,selection,q["point"],q["price_decimal"],observed,
                     int((kickoff-observed).total_seconds()//60),tag,"propline",updated))
    return rows


def ingest_hourly(now=None):
    # One transaction for rows and capture log; a crash cannot leave an imported
    # snapshot unmarked and cause it to be imported again on the next cron pass.
    with conn() as connection:
        if not connection.execute("SELECT pg_try_advisory_xact_lock(739104223) AS locked").fetchone()["locked"]:
            return dict(source="propline", calls=0, rows=0, matches=0, reason="import_in_progress")
        return _ingest_hourly(connection, now)


def _ingest_hourly(connection, now=None):
    from .odds_worker import match_meta, match_events
    now = now or datetime.now(timezone.utc)
    pending = query("""SELECT m.match_id,l.odds_api_key FROM matches m JOIN leagues l USING(league_id)
        WHERE m.status='scheduled' AND l.active AND l.odds_api_key IS NOT NULL
          AND m.kickoff_utc>%s AND m.kickoff_utc<%s::timestamptz+interval '8 days'""", (now, now))
    by_sport = {}
    for row in pending:
        by_sport.setdefault(ALIASES.get(row["odds_api_key"], row["odds_api_key"]), []).append(row["match_id"])
    result = dict(source="propline", calls=0, rows=0, matches=0, stale_sports=[], sin_cobertura=[], unmatched_events=0)
    catalog = catalog_keys(now)
    for sport, ids in by_sport.items():
        events, receipt = newest(settings.propline_archive, f"/v1/sports/{sport}/odds", now)
        if receipt is None:
            # Fuera del catálogo de PropLine no hay captura posible: no es un archivo atrasado.
            # The Odds API no es fallback automático (decisión del 23-oct-2026); queda sin cuotas.
            (result["sin_cobertura"] if catalog is not None and sport not in catalog
             else result["stale_sports"]).append(sport)
            continue
        observed = parse_time(receipt["received_at"])
        tag = "hourly:" + str(receipt["request_id"])
        done = {r["match_id"] for r in connection.execute("SELECT match_id FROM odds_capture_log WHERE window_tag=%s", (tag,)).fetchall()}
        meta = match_meta([mid for mid in ids if mid not in done])
        if not meta:
            continue
        feed = football_feed(events, receipt["received_at"])
        pairs = match_events(feed, meta)
        result["unmatched_events"] += len(feed) - len(pairs)
        for event, mid in pairs:
            kickoff = meta[mid]["kickoff_utc"]
            if observed >= kickoff or abs((parse_time(event["commence_time"]) - kickoff).total_seconds()) > 900:
                continue
            original = next(e for e in events if str(e["id"]) == str(event["id"]))
            allowed = soft_allowed(observed, kickoff)
            rows = football_rows(original, mid, observed, kickoff, tag, allowed)
            if not rows:
                continue
            with connection.cursor() as cur:
                with cur.copy("""COPY odds_snapshots(match_id,bookmaker,market,selection,line,price,
                              captured_at,mins_to_kickoff,window_tag,source,book_updated_at) FROM STDIN""") as stream:
                    for row in rows:
                        stream.write_row(row)
            connection.execute("""INSERT INTO odds_capture_log(match_id,window_tag,rows_written) VALUES (%s,%s,%s)
                       ON CONFLICT(match_id,window_tag) DO NOTHING""", (mid, tag, len(rows)))
            result["rows"] += len(rows)
            result["matches"] += 1
    return result
