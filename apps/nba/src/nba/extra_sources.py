"""Public supplemental observations; no injury, identity or betting promotion."""
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import httpx

from .audit import digest, write_json
from .context import TEAM_ALIASES, utc

VERSION = "supplemental-sources-v1"
LINEUPS_URL = "https://www.rotowire.com/basketball/nba-lineups.php"
ROTATIONS_URL = "https://api.pbpstats.com/get-game-stats"


def capture_supplemental(root, game_ids=None):
    """One public page or a bounded NBA-game batch. Stop on access/rate denial."""
    if game_ids is None:
        requests = [("rotowire.html", LINEUPS_URL, None)]
        source = "RotoWire_public_lineups"
    else:
        if not 1 <= len(game_ids) <= 20 or len(set(game_ids)) != len(game_ids):
            raise ValueError("supply 1–20 unique NBA game IDs per batch")
        if any(not re.fullmatch(r"00[12456]\d{7}", g) for g in game_ids):
            raise ValueError("official NBA game IDs required")
        requests = [(f"lineup_{g}.json", ROTATIONS_URL, dict(GameId=g, Type="Lineup")) for g in game_ids]
        source = "PBPStats_public_game_lineups"
    folder = Path(root) / (datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "_" + uuid4().hex[:8])
    folder.mkdir(parents=True, exist_ok=False)
    manifest = dict(source=source, files=[], errors=[], version=VERSION, actionable=False)
    with httpx.Client(timeout=35, follow_redirects=False) as client:
        for name, url, params in requests:
            if manifest["files"] or manifest["errors"]:
                time.sleep(0.5)
            try:
                with client.stream("GET", url, params=params) as response:
                    if response.status_code != 200:
                        manifest["errors"].append(dict(name=name, status=response.status_code))
                        if response.status_code in {403, 429} or response.status_code >= 500:
                            break
                        continue
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > 5_000_000:
                            raise ValueError("supplemental response exceeds size limit")
                    path = folder / name
                    path.write_bytes(body)
                    manifest["files"].append(dict(name=name, url=str(response.url), bytes=len(body),
                        sha256=digest(path), first_received_at_utc=datetime.now(UTC).isoformat(),
                        published_at_utc=None, content_type=response.headers.get("content-type")))
            except (httpx.HTTPError, ValueError) as exc:
                manifest["errors"].append(dict(name=name, reason=type(exc).__name__))
                break
    manifest["status"] = "captured" if len(manifest["files"]) == len(requests) else "incomplete"
    write_json(folder / "manifest.json", manifest)
    return dict(manifest_path=(folder / "manifest.json").as_posix(),
                manifest_sha256=digest(folder / "manifest.json"), files=len(manifest["files"]),
                errors=manifest["errors"], actionable=False)


def supplemental_files(manifest_path):
    """Verify legacy probe receipts as well as new, immutable capture manifests."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result = {}
    for entry in manifest["files"]:
        name = entry["name"]
        if Path(name).name != name or name in result:
            raise ValueError("unsafe or duplicate supplemental filename")
        path = manifest_path.parent / name
        if digest(path) != entry["sha256"] or path.stat().st_size != entry["bytes"]:
            raise ValueError("supplemental raw integrity mismatch")
        received = entry.get("first_received_at_utc", entry.get("first_received_utc", entry.get("received_at_utc")))
        utc(received)
        result[name] = (path, entry, received)
    return manifest, result


class Node:
    def __init__(self, tag="root", attrs=()):
        self.tag, self.attrs, self.children, self.data = tag, dict(attrs), [], []

    def has(self, cls):
        return cls in self.attrs.get("class", "").split()

    def descendants(self, cls=None, tag=None):
        for child in self.children:
            if (cls is None or child.has(cls)) and (tag is None or child.tag == tag):
                yield child
            yield from child.descendants(cls, tag)

    def text(self):
        return " ".join(" ".join(self.data + [c.text() for c in self.children]).split())


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, attrs))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].data.append(data)


def parse_lineups(html):
    page = Page(html).root
    dates = {n.attrs["data-gamedate"] for n in page.descendants(tag="main") if n.attrs.get("data-sportfull") == "basketball"}
    if len(dates) != 1:
        raise ValueError("unique lineup page date required")
    page_date = dates.pop()
    date.fromisoformat(page_date)
    games, matchups = [], set()
    for card in page.descendants("lineup"):
        if not card.has("is-nba") or card.has("is-tools"):
            continue
        teams = list(card.descendants("lineup__team"))
        sides = {}
        for side, css in (("away", "is-visit"), ("home", "is-home")):
            anchors = [n for n in teams if n.has(css)]
            lists = [n for n in card.descendants("lineup__list") if n.has(css)]
            if len(anchors) != 1 or len(lists) != 1:
                raise ValueError("lineup team structure changed")
            abbrs = list(anchors[0].descendants("lineup__abbr"))
            statuses = list(lists[0].descendants("lineup__status"))
            if len(abbrs) != 1 or len(statuses) != 1:
                raise ValueError("lineup status/team missing")
            state = "confirmed_by_provider" if statuses[0].has("is-confirmed") else "expected" if statuses[0].has("is-expected") else "unknown"
            starters, medical, section = [], [], "starters"
            for node in lists[0].children:
                if node.has("lineup__title"):
                    section = "may_not_play"
                if not node.has("lineup__player"):
                    continue
                links = list(node.descendants(tag="a"))
                if len(links) != 1:
                    raise ValueError("player link ambiguous")
                link = links[0]
                match = re.fullmatch(r"/basketball/player/[^/]+-(\d+)", link.attrs.get("href", ""))
                if not match or not link.attrs.get("title"):
                    raise ValueError("provider player identity absent")
                injuries = list(node.descendants("lineup__inj"))
                row = dict(provider_player_id="rotowire:" + match[1], name=link.attrs["title"],
                    provider_injury_label=injuries[0].text() if injuries else None,
                    provider_play_likelihood_label=node.attrs.get("title"),
                    source_verified=False, nba_player_id=None)
                (starters if section == "starters" else medical).append(row)
            if len(starters) != 5 or len({x["provider_player_id"] for x in starters}) != 5:
                raise ValueError("five distinct starters required")
            team = abbrs[0].text()
            sides[side] = dict(team=TEAM_ALIASES.get(team, team), status=state,
                               starters=starters, may_not_play=medical)
        key = tuple(sides[s]["team"] for s in ("away", "home"))
        if key in matchups or key[0] == key[1]:
            raise ValueError("duplicate/invalid lineup matchup")
        matchups.add(key)
        clocks = list(card.descendants("lineup__time"))
        if len(clocks) != 1:
            raise ValueError("lineup clock missing")
        games.append(dict(page_date=page_date, displayed_time_et=clocks[0].text(), **sides))
    if not games:
        raise ValueError("no public NBA lineup cards")
    return games


def audit_lineups(lineup_manifest, context_manifest, as_of):
    now = utc(as_of)
    meta, raw = supplemental_files(lineup_manifest)
    if meta["source"] not in {"RotoWire_public_lineups", "public_lineup_rotation_probe"}:
        raise ValueError("unexpected lineup capture source")
    path, entry, received = raw["rotowire.html"]
    if entry["url"] != LINEUPS_URL or utc(received) > now:
        raise ValueError("wrong lineup URL or future capture")
    context, files = supplemental_files(context_manifest)
    requested_date = context["date_requested"]
    if context["source"] != "NBA_ESPN_public_context":
        raise ValueError("ESPN calendar capture required")
    scoreboard_path, _, calendar_received = files[f"scoreboard_{requested_date.replace('-', '')}.json"]
    if utc(calendar_received) > now:
        raise ValueError("future calendar capture")
    calendar = defaultdict(list)
    for event in json.loads(scoreboard_path.read_text(encoding="utf-8"))["events"]:
        competition = event["competitions"][0]
        teams = {c["homeAway"]: TEAM_ALIASES.get(c["team"]["abbreviation"], c["team"]["abbreviation"]) for c in competition["competitors"]}
        calendar[(teams["away"], teams["home"])].append(event)
    games = parse_lineups(path.read_text(encoding="utf-8"))
    for game in games:
        candidates = calendar[(game["away"]["team"], game["home"]["team"])]
        event = candidates[0] if len(candidates) == 1 and game["page_date"] == requested_date else None
        tip = utc(event["date"]) if event else None
        # The display clock stays raw ET. A unique calendar match supplies UTC;
        # this is a candidate link until clocks/lineup identities are independently verified.
        game.update(candidate_event_id="espn:" + str(event["id"]) if event else None,
                    candidate_tipoff_utc=tip.isoformat() if tip else None,
                    captured_before_candidate_tip=utc(received) < tip if tip else None,
                    first_received_at_utc=received, published_at_utc=None,
                    event_link_verified=False, actionable=False)
    states = Counter(g[s]["status"] for g in games for s in ("home", "away"))
    return dict(version=VERSION, as_of=as_of, games=games,
                summary=dict(games=len(games), team_lineups=sum(states.values()), states=dict(states),
                             starters=sum(len(g[s]["starters"]) for g in games for s in ("home", "away")),
                             candidate_calendar_matches=sum(g["candidate_event_id"] is not None for g in games)),
                input_hashes={str(lineup_manifest): digest(lineup_manifest), str(context_manifest): digest(context_manifest)},
                limits=["provider IDs remain separate from NBA IDs", "expected is not confirmed or medically available",
                        "capture time is not historical publication time", "ET display clock and candidate event links are unverified"],
                actionable=False)


def _seconds(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{2,3}:[0-5]\d", value):
        raise ValueError("invalid lineup minutes")
    minutes, seconds = map(int, value.split(":"))
    return minutes * 60 + seconds


def _count(value):
    if type(value) is not int or value < 0:
        raise ValueError("invalid count statistic")
    return value


def audit_rotation_game(data, game_id, box_rows):
    """Quarter aggregates, never chronological stints or individual rebound counts.

    Reported MM:SS aggregates have a conservative +/-1 second quantization
    allowance per row, plus one second for the independent box-score clock.
    No clocks are rescaled to force agreement. Scores must agree exactly.
    """
    if not re.fullmatch(r"00[12456]\d{7}", game_id) or data["league"] != "nba":
        raise ValueError("NBA namespace required")
    rows = [r for r in box_rows if r["game_id"] == game_id]
    if not rows or len({r["player_id"] for r in rows}) != len(rows):
        raise ValueError("complete unique box-score reference required")
    if {r["date"] for r in rows} != {data["date"]} or {r["season"] for r in rows} != {data["season"]}:
        raise ValueError("game date/season mismatch")
    types = {"regular": "Regular Season", "playoffs": "Playoffs", "preseason": "Pre Season"}
    if {types.get(r["season_type"]) for r in rows} != {data["season_type"]}:
        raise ValueError("game season type mismatch")
    teams = {int(data["home_team_id"]), int(data["away_team_id"])}
    if len(teams) != 2 or teams != {r["team_id"] for r in rows}:
        raise ValueError("game team identity mismatch")
    output, exposures, errors, period_sets = [], [], [], []
    for side in ("Home", "Away"):
        tid = int(data[side.lower() + "_team_id"])
        team_rows = {r["player_id"]: r for r in rows if r["team_id"] == tid}
        periods = data["stats"][side]
        numeric = sorted(int(k) for k in periods if re.fullmatch(r"[1-9]\d*", k))
        if numeric != list(range(1, len(numeric) + 1)) or not 4 <= len(numeric) <= 12 or set(periods) != {str(k) for k in numeric} | {"FullGame"}:
            raise ValueError("invalid/missing periods")
        period_sets.append(numeric)
        aggregates = defaultdict(lambda: [0, 0, 0])
        full_seconds, full_counts = Counter(), Counter()
        for period in [str(k) for k in numeric] + ["FullGame"]:
            duration = 2880 + 300 * (len(numeric) - 4) if period == "FullGame" else 720 if int(period) <= 4 else 300
            lineups = periods[period]
            if not isinstance(lineups, list) or not lineups:
                raise ValueError("empty lineup period")
            seen, clock, points = set(), 0, 0
            for row in lineups:
                parts = row["EntityId"].split("-")
                if len(parts) != 5 or any(not re.fullmatch(r"[1-9]\d*", p) for p in parts):
                    raise ValueError("five official player IDs required")
                pids = tuple(sorted(map(int, parts)))
                if len(set(pids)) != 5 or pids in seen or not set(pids) <= team_rows.keys():
                    raise ValueError("duplicate/wrong-team lineup identities")
                if any(not team_rows[p]["participated"] for p in pids):
                    raise ValueError("DNP player appears in lineup")
                seen.add(pids)
                seconds = _seconds(row.get("Minutes", "00:00"))
                if seconds > duration:
                    raise ValueError("lineup clock exceeds period")
                clock += seconds
                pts = _count(row.get("Points", 0))
                points += pts
                if period == "FullGame":
                    previous_seconds, previous_count, previous_points = aggregates[pids]
                    if abs(seconds - previous_seconds) > previous_count + 1:
                        raise ValueError("quarter/full-game lineup clocks disagree")
                    if pts != previous_points:
                        raise ValueError("quarter/full-game lineup scores disagree")
                    for pid in pids:
                        full_seconds[pid] += seconds
                        full_counts[pid] += 1
                else:
                    aggregates[pids][0] += seconds
                    aggregates[pids][1] += 1
                    aggregates[pids][2] += pts
                    output.append(dict(game_id=game_id, date=data["date"], season=data["season"], team_id=tid,
                        period=int(period), nba_player_ids=list(pids), reported_seconds=seconds,
                        seconds_quantization_allowance=1, points=pts,
                        offensive_possessions=_count(row.get("OffPoss", 0)),
                        defensive_possessions=_count(row.get("DefPoss", 0))))
            if period == "FullGame" and seen != set(aggregates):
                raise ValueError("full-game lineup census differs from quarters")
            if abs(clock - duration) > len(lineups):
                raise ValueError("lineup clock does not cover period")
            team = data["team_results"][side][period]
            if _seconds(team["Minutes"]) != duration or points != _count(team.get("Points", 0)):
                raise ValueError("team clock/score mismatch")
            if period == "FullGame" and points != sum(r["points"] for r in team_rows.values()):
                raise ValueError("box-score points mismatch")
            errors.append(dict(team_id=tid, period=period, reported_clock_error_seconds=clock - duration,
                               allowed_quantization_seconds=len(lineups)))
        for pid, row in team_rows.items():
            box_seconds = round((row["minutes"] or 0) * 60)
            if abs(full_seconds[pid] - box_seconds) > full_counts[pid] + 1:
                raise ValueError("box-score player minutes mismatch")
            exposures.append(dict(game_id=game_id, team_id=tid, player_id=pid, reported_seconds=full_seconds[pid],
                reference_seconds=box_seconds, error_seconds=full_seconds[pid] - box_seconds,
                allowed_quantization_seconds=full_counts[pid] + 1))
    if period_sets[0] != period_sets[1]:
        raise ValueError("teams disagree on overtime periods")
    return dict(game_id=game_id, date=data["date"], season=data["season"], periods=len(period_sets[0]),
                quarter_lineups=output, player_exposures=exposures, clock_errors=errors)


def audit_rotations(manifest_path, box_rows):
    meta, files = supplemental_files(manifest_path)
    if meta["source"] not in {"PBPStats_public_game_lineups", "public_lineup_rotation_probe"}:
        raise ValueError("unexpected rotations source")
    by_game = defaultdict(list)
    for row in box_rows:
        by_game[row["game_id"]].append(row)
    accepted, rejected = [], []
    for name, (path, entry, received) in files.items():
        match = re.fullmatch(r"lineup_(00[12456]\d{7})\.json", name)
        if not match:
            continue
        game_id = match[1]
        url = urlparse(entry["url"])
        if url.scheme != "https" or url.netloc != "api.pbpstats.com" or url.path != "/get-game-stats" or parse_qs(url.query) != {"GameId": [game_id], "Type": ["Lineup"]}:
            raise ValueError("rotation URL identity mismatch")
        try:
            game = audit_rotation_game(json.loads(path.read_text(encoding="utf-8")), game_id, by_game[game_id])
            game.update(first_received_at_utc=received, historically_available_at_tipoff=False)
            accepted.append(game)
        except (ValueError, KeyError, TypeError) as exc:
            rejected.append(dict(game_id=game_id, reason=str(exc)))
    return dict(version=VERSION, games=accepted, quarantined=rejected,
        summary=dict(accepted_games=len(accepted), quarantined_games=len(rejected),
                     quarter_lineups=sum(len(g["quarter_lineups"]) for g in accepted),
                     overtime_games=sum(g["periods"] > 4 for g in accepted)),
        input_hashes={str(manifest_path): digest(manifest_path)}, actionable=False,
        limits=["aggregates by quarter, not chronological substitution stints",
                "historical capture has no original publication/revision times",
                "PBP team rebounds are not individual player rebounds", "clock quantization is retained, never rescaled"])
