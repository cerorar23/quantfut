"""Shared hourly PropLine archive. Standard library only; also runs on the host.

One network reader, many offline consumers. Raw responses are immutable gzip
objects; SQLite indexes receipts and reserves requests before network access.
Prices stay American in the original. Period/team/DFS metadata is never lost.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import shutil
import tempfile
import unicodedata
from datetime import datetime, timedelta, timezone
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.prop-line.com"
UTC = timezone.utc
VERSION = "propline-shared-1"
SAFE_KEY = re.compile(r"[a-z][a-z0-9_]*\Z")
# Market keys may start with a digit ("2plus_goals"); sport keys may not.
MARKET_KEY = re.compile(r"[a-z0-9][a-z0-9_]*\Z")
SAFE_EVENT = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
# Per-event bodies are one object, not a list of events.
EVENT_OBJECT = re.compile(r"/events/[A-Za-z0-9_-]+/(?:odds/closing|results|stats)\Z")
SETTLED = ("final", "retired", "walkover")
SAFE_HEADERS = ("date", "content-type", "x-daily-limit", "x-daily-used",
                "x-daily-remaining", "x-daily-reset", "retry-after",
                "x-propline-missing-markets")


def utcnow():
    return datetime.now(UTC)


def stamp(value):
    if value.tzinfo is None:
        raise ValueError("timezone required")
    return value.astimezone(UTC).isoformat()


def parse_time(value):
    result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timezone required")
    return result.astimezone(UTC)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf8")


class BudgetStop(Exception):
    pass


def connect(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(root / "index.sqlite", timeout=30)
    db.row_factory = sqlite3.Row
    db.executescript("""
      PRAGMA journal_mode=WAL;
      CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY, slot TEXT NOT NULL, path TEXT NOT NULL,
        params TEXT NOT NULL, started_at TEXT NOT NULL, state TEXT NOT NULL,
        UNIQUE(slot,path,params));
      CREATE TABLE IF NOT EXISTS receipts (
        request_id INTEGER PRIMARY KEY REFERENCES requests(id),
        received_at TEXT NOT NULL, status INTEGER NOT NULL, sha256 TEXT NOT NULL,
        body_path TEXT NOT NULL, headers TEXT NOT NULL, error TEXT,
        events INTEGER NOT NULL, outcomes INTEGER NOT NULL);
      CREATE INDEX IF NOT EXISTS receipts_time ON receipts(received_at);
      CREATE TRIGGER IF NOT EXISTS immutable_receipts_update BEFORE UPDATE ON receipts
        BEGIN SELECT RAISE(ABORT,'immutable receipt'); END;
      CREATE TRIGGER IF NOT EXISTS immutable_receipts_delete BEFORE DELETE ON receipts
        BEGIN SELECT RAISE(ABORT,'immutable receipt'); END;
    """)
    return db


def put_object(root, body):
    sha = hashlib.sha256(body).hexdigest()
    relative = Path("objects") / sha[:2] / (sha + ".json.gz")
    path = Path(root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    # Publish a complete object atomically; a killed process cannot leave a
    # truncated file at the permanent content-addressed path.
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        temporary = Path(f.name)
        f.write(gzip.compress(body, mtime=0))
        f.flush()
        os.fsync(f.fileno())
    try:
        try:
            if os.name == "nt":
                os.rename(temporary, path)  # Windows rename refuses an existing destination.
            else:
                os.link(temporary, path)
        except FileExistsError:
            if hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest() != sha:
                raise ValueError("corrupt archive object")
    finally:
        temporary.unlink(missing_ok=True)
    return sha, relative.as_posix()


def load_object(root, receipt):
    path = Path(root) / receipt["body_path"]
    body = gzip.decompress(path.read_bytes())
    if hashlib.sha256(body).hexdigest() != receipt["sha256"]:
        raise ValueError("archive hash mismatch")
    return json.loads(body)


def market_identity(market):
    """Do not collapse alternate ladders that share a key and description."""
    legs = sorted(canonical([o.get(k) for k in ("outcome_id","book_outcome_id","name","description","point")])
                  for o in market.get("outcomes", []))
    return (market["key"],market.get("period"),market.get("team"),market.get("description"),
            market.get("line_type"),tuple(legs))


def read_key(path):
    text = Path(path).read_text(encoding="utf-8-sig").strip()
    if "=" not in text and "\n" not in text:
        value = text
    else:
        pairs = dict(line.split("=", 1) for line in text.splitlines()
                     if "=" in line and not line.lstrip().startswith("#"))
        value = pairs.get("PROPLINE_API_KEY", pairs.get("PROPLINE_KEY", "")).strip().strip("\"'")
    if not re.fullmatch(r"[A-Za-z0-9_-]{16,160}", value):
        raise ValueError("missing or malformed PropLine key")
    return value


def transport(path, params, key):
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"X-API-Key": key,
        "User-Agent": "QuantFut-SharedArchive/1", "Accept": "application/json"})
    try:
        response = urllib.request.urlopen(req, timeout=120)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        # Bound an unexpectedly large response; a transport failure remains reserved.
        body = response.read(160 * 1024 * 1024 + 1)
        if len(body) > 160 * 1024 * 1024:
            raise ValueError("response exceeds archive size limit")
        return response.status, dict(response.headers.items()), body


class Collector:
    def __init__(self, root, key, *, daily_cap=4000, reserve=500,
                 get=transport, clock=utcnow):
        if not 1 <= daily_cap <= 4500 or reserve < 500:
            raise ValueError("daily cap must be <=4500, reserve >=500")
        self.root, self.key = Path(root), key
        self.cap, self.reserve, self.get, self.clock = daily_cap, reserve, get, clock
        self.db = connect(root)

    def capture(self, path, params=None, *, daily=False, cap=None):
        if not re.fullmatch(r"/v1/sports(?:/[a-z][a-z0-9_]*(?:/(?:odds|scores|ids|futures|injuries)"
                            r"|/events/[A-Za-z0-9_-]+/(?:markets|odds/closing|results|stats))?)?", path):
            raise ValueError("unsupported capture path")
        params = params or {}
        if shutil.disk_usage(self.root).free < 5 * 1024**3:
            raise BudgetStop("archive_disk_reserve")
        now = self.clock()
        slot = stamp(now.replace(hour=0 if daily else now.hour, minute=0, second=0, microsecond=0))
        encoded = canonical(params).decode("utf8")
        day = stamp(now.replace(hour=0, minute=0, second=0, microsecond=0))
        tomorrow = stamp(now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))
        self.db.execute("BEGIN IMMEDIATE")
        try:
            old = self.db.execute("SELECT id FROM requests WHERE slot=? AND path=? AND params=?",
                                  (slot, path, encoded)).fetchone()
            if old:
                self.db.commit()
                return self.db.execute("SELECT * FROM receipts WHERE request_id=?", (old["id"],)).fetchone(), False
            calls = self.db.execute("SELECT count(*) FROM requests WHERE started_at>=? AND started_at<?",
                                    (day, tomorrow)).fetchone()[0]
            if calls >= (self.cap if cap is None else min(self.cap, cap)):
                raise BudgetStop("local_daily_cap")
            latest = self.db.execute("SELECT received_at,headers FROM receipts ORDER BY request_id DESC LIMIT 1").fetchone()
            if latest:
                h = json.loads(latest["headers"])
                remaining, reset = h.get("x-daily-remaining"), h.get("x-daily-reset")
                if remaining is not None and reset is not None and now.timestamp() < int(reset):
                    if int(remaining) <= self.reserve:
                        raise BudgetStop("account_reserve")
            cur = self.db.execute("INSERT INTO requests(slot,path,params,started_at,state) VALUES (?,?,?,?,?)",
                                  (slot, path, encoded, stamp(now), "reserved"))
            rid = cur.lastrowid
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise
        try:
            status, headers, body = self.get(path, params, self.key)
        except Exception as exc:
            # Do not persist exception text (URLs/keys can occur in network errors).
            self.db.execute("UPDATE requests SET state=? WHERE id=?", ("transport_" + type(exc).__name__, rid))
            self.db.commit()
            return None, True
        received = stamp(self.clock())
        headers = {k.lower(): str(v) for k, v in headers.items() if k.lower() in SAFE_HEADERS}
        sha, file = put_object(self.root, body)
        events = outcomes = 0
        error = None
        try:
            payload = json.loads(body)
            if status == 200 and isinstance(payload, dict) and EVENT_OBJECT.search(path):
                payload = [payload]
            if status == 200 and isinstance(payload, dict) and path.endswith("/injuries"):
                payload = payload.get("players", [])  # one "event" per listed player
            if status == 200 and not isinstance(payload, list):
                raise ValueError("list payload required")
            if status == 200:
                events = len(payload)
                outcomes = sum(len(m.get("outcomes", [])) for e in payload if isinstance(e, dict)
                               for b in e.get("bookmakers", []) for m in b.get("markets", []))
        except (ValueError, TypeError, AttributeError):
            error = "invalid_json_shape"
        self.db.execute("INSERT INTO receipts VALUES (?,?,?,?,?,?,?,?,?)",
                        (rid, received, status, sha, file, json.dumps(headers), error, events, outcomes))
        self.db.execute("UPDATE requests SET state=? WHERE id=?", ("complete", rid))
        self.db.commit()
        row = self.db.execute("SELECT * FROM receipts WHERE request_id=?", (rid,)).fetchone()
        if status in (401, 403, 429):
            raise BudgetStop("provider_http_" + str(status))
        return row, True


def newest(root, path, as_of, *, max_age_seconds=3900):
    """Offline, point-in-time read. A late receipt never becomes an earlier feature."""
    db_path = Path(root) / "index.sqlite"
    if not db_path.is_file():
        return None, None
    db = sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        row = db.execute("""SELECT p.*,q.started_at,q.slot FROM receipts p JOIN requests q ON q.id=p.request_id
          WHERE q.path=? AND p.status=200 AND p.error IS NULL AND p.received_at<=?
          ORDER BY p.received_at DESC,p.request_id DESC LIMIT 1""", (path, stamp(as_of))).fetchone()
        if row is None or (as_of - parse_time(row["received_at"])).total_seconds() > max_age_seconds:
            return None, None
        if not path.endswith("/odds"):
            return load_object(root, row), dict(row)
        # PropLine accepts at most 50 market keys per request. Merge disjoint
        # batches of this hourly observation only, never a previous hour.
        parts = db.execute("""SELECT p.* FROM receipts p JOIN requests q ON q.id=p.request_id
              WHERE q.path=? AND q.slot=? AND p.status=200 AND p.error IS NULL AND p.received_at<=?
              ORDER BY p.received_at,p.request_id""", (path,row["slot"],stamp(as_of))).fetchall()
        merged = {}
        for part in parts:
            for event in load_object(root, part):
                eid = str(event["id"])
                old = merged.get(eid, {})
                books = {b["key"]: b for b in old.get("bookmakers", [])}
                for book in event.get("bookmakers", []):
                    markets = {market_identity(m): m
                               for m in books.get(book["key"], {}).get("markets", [])}
                    markets.update({market_identity(m): m for m in book.get("markets", [])})
                    books[book["key"]] = dict(book, markets=list(markets.values()))
                merged[eid] = dict(event, bookmakers=list(books.values()))
        return list(merged.values()), dict(row, component_receipts=[p["request_id"] for p in parts])
    finally:
        db.close()


def decimal_price(outcome):
    explicit = outcome.get("price_decimal")
    if explicit is not None:
        p = float(explicit)
    else:
        raw = float(outcome["price"])
        if abs(raw) < 100 or not math.isfinite(raw):
            raise ValueError("invalid American odds")
        p = 1 + (raw / 100 if raw > 0 else 100 / -raw)
    if not math.isfinite(p) or p <= 1:
        raise ValueError("invalid decimal odds")
    return p


DFS_BOOKS = {"prizepicks", "underdog", "sleeper", "dabble", "parlayplay", "draftkings_pick6"}
EXCHANGES = {"kalshi", "polymarket", "polymarket_us", "matchbook", "smarkets", "novig", "prophetx", "sx_bet", "betfair_exchange"}


def quotes(events, received_at):
    """Lossless context + explicit price semantics for training/consumer adapters."""
    received = parse_time(received_at)
    for e in events:
        kickoff = parse_time(e["commence_time"])
        for b in e.get("bookmakers", []):
            for m in b.get("markets", []):
                for o in m.get("outcomes", []):
                    try:
                        price = decimal_price(o)
                    except (KeyError, ValueError, TypeError):
                        price = None
                    # last_seen_at is delivery; book_updated_at remains unknown if absent.
                    flags = []
                    if e.get("live") or kickoff <= received:
                        flags.append("in_play_or_started")
                    if e.get("is_outright"):
                        flags.append("outright")
                    if m.get("suspended_at"):
                        flags.append("suspended")
                    if b["key"] in DFS_BOOKS:
                        flags.append("dfs_not_single_bet")
                    if b["key"] in EXCHANGES:
                        flags.append("exchange_contract_requires_rules")
                    if b.get("pregame_only") and e.get("live"):
                        flags.append("frozen_pregame_book")
                    if price is None:
                        flags.append("invalid_price")
                    if o.get("point") is not None:
                        try:
                            if not math.isfinite(float(o["point"])):
                                flags.append("invalid_point")
                        except (ValueError,TypeError):
                            flags.append("invalid_point")
                    if o.get("last_seen_at"):
                        try:
                            delivery_age=(received-parse_time(o["last_seen_at"])).total_seconds()
                            if delivery_age>900:
                                flags.append("stale_provider_delivery")
                            if delivery_age < -2:
                                flags.append("future_provider_delivery")
                        except (ValueError,TypeError):
                            flags.append("invalid_provider_delivery")
                    allowed = o.get("allowed_wager_types")
                    if allowed == "over" and o.get("name") == "Under":
                        flags.append("restricted_side")
                    if o.get("book_updated_at"):
                        try:
                            if parse_time(o["book_updated_at"]) > received:
                                flags.append("future_book_update")
                        except (ValueError, TypeError):
                            flags.append("invalid_book_update")
                    yield dict(provider="propline", received_at=received_at,
                        event_id=str(e["id"]), sport_key=e.get("sport_key"), commence_time=e["commence_time"],
                        home_team=e.get("home_team"), away_team=e.get("away_team"),
                        home_team_id=e.get("home_team_id"), away_team_id=e.get("away_team_id"),
                        merged_from_event_ids=e.get("merged_from_event_ids"), tour=e.get("tour"), tournament=e.get("tournament"),
                        bookmaker=b["key"], book_event_id=b.get("book_event_id"),
                        market=m["key"], period=m.get("period"), team=m.get("team"),
                        market_description=m.get("description"), line_type=m.get("line_type"),
                        name=o.get("name"), description=o.get("description"), side=o.get("side"),
                        player_id=o.get("player_id"), outcome_id=o.get("outcome_id"), book_outcome_id=o.get("book_outcome_id"),
                        point=o.get("point"), price_american=o.get("price"), price_decimal=price,
                        book_updated_at=o.get("book_updated_at"), last_change_at=o.get("last_change_at"),
                        last_seen_at=o.get("last_seen_at"), dfs_odds_type=o.get("dfs_odds_type"),
                        payout_multiplier=o.get("payout_multiplier"), allowed_wager_types=o.get("allowed_wager_types"),
                        liquidity=o.get("liquidity"), flags=flags)


def football_feed(events, received_at):
    """Only unambiguous full-game sportsbook lines; never relabel team totals/periods."""
    result = []
    for e in events:
        usable = [q for q in quotes([e], received_at) if not q["flags"]
                  and q["period"] is None and q["team"] is None
                  and q["market"] in ("h2h", "totals", "spreads")
                  and q["line_type"] in (None, "main")]
        books = {}
        for q in usable:
            if q["market"] == "h2h" and q["side"] not in ("home", "away", "draw"):
                continue
            if q["market"] == "spreads" and q["side"] not in ("home", "away"):
                continue
            if q["market"] == "totals" and q["name"] not in ("Over", "Under"):
                continue
            b = books.setdefault(q["bookmaker"], {})
            pair = (q["market"], q["point"] if q["market"] == "totals" else None)
            m = b.setdefault(pair, {"key": q["market"], "outcomes": []})
            name = ({"home": e["home_team"], "away": e["away_team"], "draw": "Draw"}.get(q["side"], q["name"]))
            m["outcomes"].append(dict(name=name, price=q["price_decimal"], point=q["point"],
                                       book_updated_at=q["book_updated_at"]))
        if books:
            result.append(dict(e, bookmakers=[dict(key=k, markets=list(v.values())) for k, v in books.items()],
                               _provider="propline", _received_at=received_at))
    return result


def two_way_feed(events, received_at):
    """Líneas completas de casas de apuestas de NBA y tenis, con la forma de The Odds API.

    Solo moneyline (`h2h`), hándicap (`spreads`) y totales (`totals`) del partido completo y línea
    principal. Dos resultados: NBA y tenis no tienen empate. `last_update` aparece solo si la casa
    publicó `book_updated_at`; nunca se rellena con la hora de recepción (desconocido ≠ reciente).
    """
    result = []
    for e in events:
        books = {}
        for q in quotes([e], received_at):
            if (q["flags"] or q["period"] is not None or q["team"] is not None or q["player_id"] is not None
                    or q["line_type"] not in (None, "main") or q["market"] not in ("h2h", "spreads", "totals")):
                continue
            if q["market"] == "totals":
                if q["name"] not in ("Over", "Under") or q["point"] is None:
                    continue
                name = q["name"]
            elif q["side"] in ("home", "away"):
                name = e["home_team"] if q["side"] == "home" else e["away_team"]
                if q["market"] == "spreads" and q["point"] is None:
                    continue
            else:
                continue
            book = books.setdefault(q["bookmaker"], {})
            market = book.setdefault((q["market"], q["point"] if q["market"] == "totals" else None),
                                     {"key": q["market"], "outcomes": []})
            outcome = dict(name=name, price=q["price_decimal"], point=q["point"])
            if q["book_updated_at"]:
                outcome["last_update"] = q["book_updated_at"]
                market["last_update"] = max(market.get("last_update", ""), q["book_updated_at"])
            market["outcomes"].append(outcome)
        # Un mercado con solo un lado no sirve para quitar el margen.
        books = {k: {m: v for m, v in b.items() if len(v["outcomes"]) == 2} for k, b in books.items()}
        books = {k: b for k, b in books.items() if b}
        if books:
            result.append(dict(e, bookmakers=[dict(key=k, markets=list(b.values()),
                    **({"last_update": max(m["last_update"] for m in b.values() if "last_update" in m)}
                       if any("last_update" in m for m in b.values()) else {})) for k, b in books.items()],
                _provider="propline", _received_at=received_at))
    return result


def read_two_way(root, sport, as_of, *, max_age_seconds=3900):
    """Lectura sin red y punto en el tiempo para `basketball_nba` o `tennis`: (eventos, recibo) o (None, None)."""
    if sport != "basketball_nba" and not sport.startswith("tennis"):
        raise ValueError("solo NBA y tenis")
    events, receipt = newest(root, f"/v1/sports/{sport}/odds", as_of, max_age_seconds=max_age_seconds)
    if receipt is None:
        return None, None
    return two_way_feed(events, receipt["received_at"]), receipt


SETTLEMENT_MAX_AGE = 45 * 86400  # a closing line or box score does not age; this only bounds the lookup


def read_injuries(root, sport, as_of, *, max_age_seconds=3900):
    """Injury report as observed at our receipt (point in time): (players, receipt) or (None, None)."""
    doc, receipt = newest(root, f"/v1/sports/{sport}/injuries", as_of, max_age_seconds=max_age_seconds)
    if receipt is None:
        return None, None
    return [dict(p, received_at=receipt["received_at"]) for p in doc.get("players", [])], receipt


def read_closing(root, sport, event_id, as_of):
    """Opening and closing line per (book, market, outcome) for one event, with explicit price semantics.

    `closing_at` is the provider's last snapshot at or before kickoff. A capture made before kickoff is
    not a close and is flagged `pre_kickoff_capture`.
    """
    doc, receipt = newest(root, f"/v1/sports/{sport}/events/{event_id}/odds/closing", as_of,
                          max_age_seconds=SETTLEMENT_MAX_AGE)
    if receipt is None:
        return None, None
    early = bool(doc.get("commence_time")) and parse_time(receipt["received_at"]) < parse_time(doc["commence_time"])
    rows = []
    for b in doc.get("bookmakers", []):
        for m in b.get("markets", []):
            for o in m.get("outcomes", []):
                flags = []
                try:
                    price = decimal_price(o)
                except (KeyError, ValueError, TypeError):
                    price = None
                    flags.append("invalid_price")
                if o.get("is_stale"):
                    flags.append("stale_close")
                if early:
                    flags.append("pre_kickoff_capture")
                if b["key"] in DFS_BOOKS or o.get("dfs_odds_type"):
                    flags.append("dfs_not_single_bet")
                if b["key"] in EXCHANGES:
                    flags.append("exchange_contract_requires_rules")
                if o.get("redacted"):
                    flags.append("redacted")
                rows.append(dict(provider="propline", received_at=receipt["received_at"], event_id=str(doc.get("id")),
                    sport_key=doc.get("sport_key"), commence_time=doc.get("commence_time"), bookmaker=b["key"],
                    market=m["key"], period=m.get("period"), team=m.get("team"), line_type=m.get("line_type"),
                    name=o.get("name"), description=o.get("description"), player_id=o.get("player_id"),
                    outcome_id=o.get("outcome_id"), point=o.get("point"), price_american=o.get("price"),
                    price_decimal=price, closing_at=o.get("closing_at"), opening_price=o.get("opening_price"),
                    opening_point=o.get("opening_point"), opening_at=o.get("opening_at"), flags=flags))
    return rows, receipt


def read_results(root, sport, event_id, as_of):
    """Provider grading per (book, market, outcome): resolution won/lost/push/void (None = not graded yet)."""
    doc, receipt = newest(root, f"/v1/sports/{sport}/events/{event_id}/results", as_of,
                          max_age_seconds=SETTLEMENT_MAX_AGE)
    if receipt is None:
        return None, None
    return [dict(event_id=str(doc.get("id")), status=doc.get("status"), bookmaker=b["key"], market=m["key"],
                 period=m.get("period"), team=m.get("team"), name=o.get("name"), description=o.get("description"),
                 player_id=o.get("player_id"), point=o.get("point"), price_american=o.get("price"),
                 resolution=o.get("resolution"), actual_value=o.get("actual_value"),
                 resolved_at=o.get("resolved_at"), redacted=bool(o.get("redacted")), received_at=receipt["received_at"])
            for b in doc.get("bookmakers", []) for m in b.get("markets", []) for o in m.get("outcomes", [])], receipt


def read_stats(root, sport, event_id, as_of):
    """Box score as captured: (body, receipt). Official only when body['status'] is final."""
    return newest(root, f"/v1/sports/{sport}/events/{event_id}/stats", as_of, max_age_seconds=SETTLEMENT_MAX_AGE)


def _fold(name):
    plain = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", plain.lower())


TEAM_STATS = ("corners", "cards")


def _same_club(a, b):
    """Folded names that are equal or where one contains the other ("ipswich" / "ipswichtown")."""
    return bool(a and b) and (a == b or (min(len(a), len(b)) >= 4 and (a in b or b in a)))


def team_sides(doc):
    """{box-score team name: 'home'|'away'}; {} when the two clubs cannot be told apart for certain.

    Books and the box score spell clubs differently ("Stuttgart" / "VfB Stuttgart", "Borussia
    M'gladbach" / "Borussia Mönchengladbach"). A name matches a side when one folded name contains the
    other; with exactly two clubs, one certain match decides the other. Anything ambiguous returns {}.
    """
    names = sorted({r.get("player_name") for r in doc.get("stats", []) if r.get("stat_type") in TEAM_STATS
                    and r.get("player_name")})
    if len(names) != 2:
        return {}
    event = {"home": _fold(doc.get("home_team")), "away": _fold(doc.get("away_team"))}
    found = {}
    for name in names:
        hits = [side for side, folded in event.items() if _same_club(_fold(name), folded)]
        if len(hits) == 1:
            found[name] = hits[0]
    if len(set(found.values())) != len(found):
        return {}
    if len(found) == 1:
        (known, side), = found.items()
        found[next(n for n in names if n != known)] = "away" if side == "home" else "home"
    return found if len(found) == 2 else {}


def team_stats(doc):
    """{'home'|'away': {'corners': n, 'cards': n}} from the box score's team rows; {} if the sides are uncertain."""
    sides = team_sides(doc)
    out = {}
    for row in doc.get("stats", []):
        side = sides.get(row.get("player_name"))
        if side and row.get("stat_type") in TEAM_STATS and row.get("stat_value") is not None:
            out.setdefault(side, {})[row["stat_type"]] = float(row["stat_value"])
    return out


def market_batches(sport, markets, config):
    """Provider-safe batches with a stable, auditable request count."""
    requested = list(dict.fromkeys(markets))
    default_size = min(50,max(1,int(config.get("max_markets_per_request",50))))
    featured = [m for m in requested if m in ("h2h","spreads","totals")]
    extended = [m for m in requested if m not in featured]
    if sport.startswith("basketball_"):
        core = [m for m in extended if m in ("player_points","player_rebounds","player_assists")]
        other = [m for m in extended if m not in core]
        return ([featured] if featured else []) + [[m] for m in core] + [other[i:i+5] for i in range(0,len(other),5)]
    if sport.startswith("soccer_"):
        size = min(50,max(1,int(config.get("soccer_markets_per_request",13))))
        return ([featured] if featured else []) + [extended[i:i+size] for i in range(0,len(extended),size)]
    if sport.startswith(("football_","americanfootball_")):
        size = min(50,max(1,int(config.get("football_markets_per_request",11))))
        return ([featured] if featured else []) + [extended[i:i+size] for i in range(0,len(extended),size)]
    return [requested[i:i+default_size] for i in range(0,len(requested),default_size)]


def select_sports(catalog, config):
    excluded = set(config.get("exclude_sports", []))
    prefixes = tuple(config.get("sport_prefixes", []))
    return [s["key"] for s in catalog if s.get("active") and SAFE_KEY.fullmatch(s["key"])
            and s["key"] not in excluded
            and (config["sports"] == "all_active" or s["key"] in config["sports"]
                 or (prefixes and s["key"].startswith(prefixes)))]


def finished_events(db, root, sport, now, settle):
    """Finished events from our own score receipts; the most-quoted first."""
    since = stamp(now - timedelta(days=int(settle.get("lookback_days", 3))))
    latest = {}
    for r in db.execute("""SELECT p.* FROM receipts p JOIN requests q ON q.id=p.request_id
            WHERE q.path=? AND p.status=200 AND p.error IS NULL AND p.received_at>=?
            ORDER BY p.received_at,p.request_id""", (f"/v1/sports/{sport}/scores", since)):
        latest.update({str(e.get("id")): e for e in load_object(root, r) if isinstance(e, dict)})
    books = {}
    ids = db.execute("""SELECT p.* FROM receipts p JOIN requests q ON q.id=p.request_id
            WHERE q.path=? AND p.status=200 AND p.error IS NULL ORDER BY p.received_at DESC LIMIT 1""",
            (f"/v1/sports/{sport}/ids",)).fetchone()
    if ids:
        books = {str(e.get("id")): len(e.get("books") or {}) for e in load_object(root, ids) if isinstance(e, dict)}
    cutoff = now - timedelta(hours=float(settle.get("min_hours_after_start", 6)))
    done = [e for i, e in latest.items() if SAFE_EVENT.fullmatch(i) and e.get("status") in SETTLED
            and e.get("commence_time") and parse_time(e["commence_time"]) <= cutoff]
    return sorted(done, key=lambda e: (-books.get(str(e["id"]), 0), e["commence_time"], str(e["id"])))


def unresolved(payload):
    """True while a results body still holds ungraded outcomes."""
    if not isinstance(payload, dict) or payload.get("redacted"):
        return False
    return any(o.get("resolution") is None for b in payload.get("bookmakers", [])
               for m in b.get("markets", []) for o in m.get("outcomes", []))


def settlement_due(db, root, path, today, max_attempts):
    """One attempt per event and UTC day. A closing line is final once
    received; results are retried while outcomes remain ungraded."""
    rows = db.execute("""SELECT q.slot,p.* FROM requests q LEFT JOIN receipts p ON p.request_id=q.id
                         WHERE q.path=? ORDER BY q.id""", (path,)).fetchall()
    if any(r["slot"] == today for r in rows) or len(rows) >= max_attempts:
        return False
    ok = [r for r in rows if r["status"] == 200 and not r["error"]]
    if not ok:
        return True
    return path.endswith("/results") and unresolved(load_object(root, ok[-1]))


def settlement_blocked(db, root, kind, today):
    """The plan cannot serve this endpoint today: stop paying for it."""
    r = db.execute("""SELECT p.* FROM receipts p JOIN requests q ON q.id=p.request_id
                      WHERE q.path LIKE ? AND q.started_at>=? ORDER BY p.request_id DESC LIMIT 1""",
                   ("%/" + kind, today)).fetchone()
    if r is None:
        return False
    if r["status"] in (401, 403):
        return True
    return r["status"] == 200 and not r["error"] and bool(load_object(root, r).get("redacted"))


def run(root, key_file, config_file, *, limit=None):
    config = json.loads(Path(config_file).read_bytes())
    client = Collector(root, read_key(key_file), daily_cap=config["daily_cap"], reserve=config["account_reserve"])
    calls = captures = events = outcomes = failures = 0
    started = utcnow()
    report = {"version": VERSION, "started_at": stamp(started), "provider": "propline"}
    settle = config.get("settlement") or {}
    settle_budget = sum(int(v) for v in settle.get("daily_budget", {}).values()) if settle.get("enabled") else 0
    # Hourly odds may not eat the part of the closing/results reserve still unspent today.
    midnight = stamp(started.replace(hour=0, minute=0, second=0, microsecond=0))
    settled_today = client.db.execute("""SELECT count(*) FROM requests WHERE started_at>=?
        AND (path LIKE '%/odds/closing' OR path LIKE '%/results' OR path LIKE '%/events/%/stats')""",
        (midnight,)).fetchone()[0]
    hourly_cap = config["daily_cap"] - max(0, settle_budget - settled_today)
    def capture(path, params=None, daily=False, cap=hourly_cap):
        nonlocal calls, captures, events, outcomes, failures
        if limit is not None and calls >= limit:
            raise BudgetStop("run_limit")
        r, called = client.capture(path, params, daily=daily, cap=cap)
        calls += int(called)
        if r is None:
            failures += 1
            return None
        if called:
            captures += 1
            events += r["events"]
            outcomes += r["outcomes"]
            print(json.dumps({"path": path, "status": r["status"], "events": r["events"], "outcomes": r["outcomes"]}), flush=True)
        if r["status"] != 200 or r["error"]:
            failures += 1
            return None
        return load_object(root, r)
    def settlement():
        if not settle.get("enabled"):
            return
        report["settlement"] = settled = {}
        now = utcnow()
        today = stamp(now.replace(hour=0, minute=0, second=0, microsecond=0))
        # Optional allowlist per budget prefix: the hourly capture keeps every soccer_* competition,
        # but settling all of them (J-League, Conference, Saudi...) in catalogue order spent the soccer
        # budget before reaching the leagues the models use (24-oct-2026: no closing for EPL games).
        only = settle.get("sports_by_prefix") or {}
        results_prefixes = settle.get("results_prefixes")
        for prefix, budget in settle["daily_budget"].items():
            spent = client.db.execute("""SELECT count(*) FROM requests WHERE started_at>=?
                AND (path LIKE ? OR path LIKE ? OR path LIKE ?)""", (today, f"/v1/sports/{prefix}%/odds/closing",
                f"/v1/sports/{prefix}%/results", f"/v1/sports/{prefix}%/events/%/stats")).fetchone()[0]
            for sport in [s for s in selected if s.startswith(prefix) and (prefix not in only or s in only[prefix])]:
                family = next((k for k in config["markets_by_family"] if sport.startswith(k)), "default")
                markets = ",".join(config["markets_by_family"][family][:50])
                counts = settled.setdefault(sport, dict(closing=0, results=0, stats=0, over_budget=0))
                for e in finished_events(client.db, root, sport, now, settle):
                    base = f"/v1/sports/{sport}/events/{e['id']}"
                    wanted = [("odds/closing", dict(markets=markets, period="all"))]
                    # retired/walkover props are void, not graded; graded props only where someone reads them
                    if e["status"] == "final" and (results_prefixes is None
                                                   or any(sport.startswith(p) for p in results_prefixes)):
                        wanted.append(("results", {}))
                    # Box score last: it only uses what closing and results leave of the reserve.
                    if any(sport.startswith(p) for p in settle.get("stats_prefixes", [])):
                        wanted.append(("stats", {}))
                    for kind, params in wanted:
                        if (settlement_blocked(client.db, root, kind, today) or not settlement_due(
                                client.db, root, f"{base}/{kind}", today, int(settle.get("max_attempts", 3)))):
                            continue
                        if spent >= int(budget):
                            counts["over_budget"] += 1
                            continue
                        spent += 1
                        capture(f"{base}/{kind}", params, daily=True, cap=config["daily_cap"])
                        counts["closing" if kind == "odds/closing" else kind] += 1
    selected = []
    try:
        sports = capture("/v1/sports")
        if sports is None:
            raise BudgetStop("catalog_unavailable")
        selected = select_sports(sports, config)
        report["sports"] = selected
        # Odds first: a slow result feed must not consume the capture window.
        for sport in selected:
            family = next((k for k in config["markets_by_family"] if sport.startswith(k)), "default")
            requested = list(config["markets_by_family"].get(family, config["markets_by_family"]["default"]))
            for r in client.db.execute("""SELECT p.* FROM receipts p JOIN requests q ON q.id=p.request_id
                       WHERE q.path LIKE ? AND p.status=200 AND p.error IS NULL""", (f"/v1/sports/{sport}/events/%/markets",)):
                requested.extend(m["key"] for m in load_object(root,r) if MARKET_KEY.fullmatch(m.get("key", "")))
            requested = list(dict.fromkeys(requested))
            planned = set(requested)
            batch_size = min(50,max(1,int(config.get("max_markets_per_request",50))))
            payload = []
            def odds(batch):
                return capture(f"/v1/sports/{sport}/odds", dict(markets=",".join(batch),
                        period="all", includeLinks="true", includeBookIds="true", includeDepth="true" if config.get("include_depth") else "false",
                        includePregameOnly="true", includeRestricted="true",
                        max_age=str(config.get("provider_max_age_seconds",3600))))
            for batch in market_batches(sport, requested, config):
                payload.extend(odds(batch) or [])
            # Once per competition/day, learn additional keys from an actual
            # fixture. The full documented family is always requested as well.
            today = stamp(utcnow().replace(hour=0,minute=0,second=0,microsecond=0))
            discovered = client.db.execute("SELECT 1 FROM requests WHERE path LIKE ? AND started_at>=? LIMIT 1",
                (f"/v1/sports/{sport}/events/%/markets",today)).fetchone()
            candidates = [e for e in payload if not e.get("is_outright") and str(e.get("id", "")).replace("-", "").replace("_", "").isalnum()]
            if candidates and not discovered:
                richest = max(candidates, key=lambda e: sum(len(m.get("outcomes", [])) for b in e.get("bookmakers", []) for m in b.get("markets", [])))
                extra = capture(f"/v1/sports/{sport}/events/{richest['id']}/markets",daily=True) or []
                missing = sorted({m["key"] for m in extra if MARKET_KEY.fullmatch(m.get("key", ""))} - planned)
                for offset in range(0,len(missing),batch_size):
                    odds(missing[offset:offset+batch_size])
        for sport in selected:
            # The run start decides: a long run must not slide into the next hour.
            if config.get("scores") and started.hour % config.get("scores_every_hours",1) == 0:
                capture(f"/v1/sports/{sport}/scores", {"days_from": 3})
            if config.get("identities_daily"):
                capture(f"/v1/sports/{sport}/ids", daily=True)
            if config.get("futures_daily"):
                capture(f"/v1/sports/{sport}/futures", daily=True)
            if sport in config.get("injuries_sports", []):
                capture(f"/v1/sports/{sport}/injuries")
        settlement()
        report["stop"] = None
    except BudgetStop as exc:
        report["stop"] = str(exc)
        if str(exc) == "local_daily_cap":
            # The hourly cap leaves the settlement reserve untouched; use it.
            try:
                settlement()
            except BudgetStop as again:
                report["settlement_stop"] = str(again)
    finally:
        report.update(finished_at=stamp(utcnow()), requests=calls, receipts=captures,
                      event_observations=events, outcome_observations=outcomes, failures=failures)
        latest = client.db.execute("SELECT headers FROM receipts ORDER BY request_id DESC LIMIT 1").fetchone()
        report["quota"] = json.loads(latest[0]) if latest else {}
        client.db.close()
    path = Path(root) / "runs"
    path.mkdir(exist_ok=True)
    (path / (report["started_at"].replace(":", "") + ".json")).write_bytes(canonical(report))
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=("capture", "latest", "export"))
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--key-file", type=Path)
    p.add_argument("--config", type=Path)
    p.add_argument("--sport")
    p.add_argument("--as-of")
    p.add_argument("--limit", type=int)
    args = p.parse_args()
    if args.command == "capture":
        if not args.key_file or not args.config:
            p.error("capture requires --key-file and --config")
        report = run(args.root, args.key_file, args.config, limit=args.limit)
        return 1 if report["failures"] or report["stop"] not in (None, "run_limit") else 0
    if args.command == "latest":
        if not args.sport or not SAFE_KEY.fullmatch(args.sport):
            p.error("latest requires a valid --sport")
        data, receipt = newest(args.root, f"/v1/sports/{args.sport}/odds", parse_time(args.as_of) if args.as_of else utcnow())
        print(json.dumps({"source": "propline", "receipt": receipt, "events": data}, ensure_ascii=False))
        return 0 if receipt else 1
    # Streaming export: receipts are ordered by our actual observation, no in-play leakage hidden.
    db = sqlite3.connect((args.root / "index.sqlite").resolve().as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    for r in db.execute("""SELECT p.*,q.path FROM receipts p JOIN requests q ON q.id=p.request_id
                 WHERE p.status=200 AND p.error IS NULL AND q.path LIKE '%/odds' ORDER BY p.received_at,p.request_id"""):
        if args.sport and r["path"] != f"/v1/sports/{args.sport}/odds":
            continue
        if args.as_of and parse_time(r["received_at"]) > parse_time(args.as_of):
            continue
        for q in quotes(load_object(args.root, r), r["received_at"]):
            print(json.dumps(dict(q, receipt_sha256=r["sha256"], receipt_id=r["request_id"]), ensure_ascii=False))
    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
