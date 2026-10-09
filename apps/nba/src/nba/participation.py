"""Source-backed subsecond participation; no inference from positive statistics."""
from collections import Counter, defaultdict
import json
import re
import unicodedata
from pathlib import Path

from .audit import digest
from .ingest import game_id, integer, minutes


def require(condition, message):
    if not condition:
        raise ValueError(message)


def full_name(first, last):
    return " ".join(unicodedata.normalize("NFC", str(first) + " " + str(last)).casefold().split())


def subsecond_proofs(sources, team_rows, player_rows):
    """Validate entire official rotations before resolving any zero MM:SS row.

    Each source supplies a local path and its independently recorded SHA256.
    Tracking times are explicit deciseconds. A resolution is limited to one
    second, blank participation status and the exact game/team/person identity.
    """
    proofs, games = {}, set()
    for source in sources:
        path = Path(source["path"])
        sha = source["sha256"]
        require(isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{64}", sha), "invalid source hash")
        require(digest(path) == sha, "rotation source hash mismatch")
        obj = json.loads(path.read_bytes())
        require(isinstance(obj, dict) and obj.get("resource") == "gamerotation", "official GameRotation required")
        gid = game_id(obj["parameters"]["GameID"])
        require(gid not in games, "duplicate rotation source for game")
        games.add(gid)
        references = [r for r in team_rows if str(r["game_id"]) == gid]
        require(len(references) == 2 and len({integer(r["team_id"]) for r in references}) == 2,
                "two distinct matching team references required")
        tids = {r["team_id"] for r in references}
        duration = float(references[0]["min"]) * 600
        require(duration in {28800 + 3000 * n for n in range(7)}
                and all(float(r["min"]) * 600 == duration for r in references), "invalid game duration")
        rows = [r for r in player_rows if str(r["gameId"]) == gid]
        players = {integer(r["personId"]): r for r in rows}
        require(rows and len(players) == len(rows) and {integer(r["teamId"]) for r in rows} == tids,
                "ambiguous or incomplete game roster")
        tables = obj["resultSets"]
        require(len(tables) == 2 and {t["name"] for t in tables} == {"HomeTeam", "AwayTeam"},
                "both official rotation teams required")
        spans, points, labels, administrative = defaultdict(list), Counter(), set(), defaultdict(list)
        for table in tables:
            headers = table["headers"]
            require(len(set(headers)) == len(headers) and table["rowSet"], "invalid rotation schema")
            table_teams = set()
            for values in table["rowSet"]:
                require(len(values) == len(headers), "rotation row/header mismatch")
                r = dict(zip(headers, values))
                pid, tid = integer(r["PERSON_ID"]), integer(r["TEAM_ID"])
                require(r["GAME_ID"] == gid and pid in players and tid == integer(players[pid]["teamId"]),
                        "rotation game/team/person mismatch")
                p = players[pid]
                require(full_name(r["PLAYER_FIRST"], r["PLAYER_LAST"]) == full_name(p["firstName"], p["familyName"]),
                        "rotation full name mismatch")
                table_teams.add(tid)
                a, b = integer(r["IN_TIME_REAL"]), integer(r["OUT_TIME_REAL"])
                pts = integer(r["PLAYER_PTS"])
                require(0 <= a <= b <= duration, "rotation interval outside game")
                points[pid] += pts
                if a == b:
                    require(pts == 0, "zero-time interval with points")
                    administrative[pid].append([a, b])
                else:
                    spans[pid].append((a, b))
            require(len(table_teams) == 1, "mixed teams in official table")
            labels.update(table_teams)
        require(labels == tids, "rotation teams incomplete")
        for pid, p in players.items():
            reported = minutes(p["minutes"], p.get("comment"))
            intervals = sorted(spans[pid])
            require(all(a[1] <= b[0] for a, b in zip(intervals, intervals[1:])), "overlapping person intervals")
            require(points[pid] == integer(p["points"]), "rotation/player points mismatch")
            exact_ticks = sum(b - a for a, b in intervals)
            if not intervals:
                require(reported is None or reported == 0, "rotation missing participant")
                continue
            require(not str(p.get("comment") or "").strip(), "positive rotation interval contradicts DNP/status")
            require(reported is not None, "positive rotation interval without reported clock")
            if reported == 0:
                require(0 < exact_ticks <= 10, "zero MM:SS cannot hide more than one second")
                proofs[(gid, pid)] = dict(source_kind="NBA GameRotation", source_path=path.as_posix(),
                    source_sha256=sha, clock_unit="deciseconds", intervals_deciseconds=[list(s) for s in intervals],
                    zero_time_intervals_deciseconds=administrative[pid], official_played_seconds=exact_ticks / 10,
                    reported_minutes_raw=p["minutes"], whole_game_intervals_validated=True)
            else:
                require(abs(exact_ticks / 10 - reported * 60) <= len(intervals) + 1e-6,
                        "rotation/player minutes mismatch")
        for tid in tids:
            own = {pid: s for pid, s in spans.items() if integer(players[pid]["teamId"]) == tid and s}
            bounds = sorted({0, duration} | {t for s in own.values() for pair in s for t in pair})
            for a, b in zip(bounds, bounds[1:]):
                floor = [pid for pid, s in own.items() if any(x <= a and y >= b for x, y in s)]
                require(len(floor) == 5, "official intervals contain a gap or non-five lineup")
    return proofs
