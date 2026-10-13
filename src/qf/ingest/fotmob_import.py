"""Importación revisable del archivo FotMob; no realiza llamadas deportivas."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import json
import logging
from pathlib import Path
import re

from ..normalize import slugify
from .fotmob_history import normalize_match, number

log = logging.getLogger(__name__)
TOLERANCE = timedelta(hours=36)
LOCK_ID = 61013062


def timestamp(value):
    result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamp_without_timezone")
    return result.astimezone(timezone.utc)


def json_write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False,
                                    allow_nan=False, default=str), encoding="utf-8")


def parse_payload(fixture, raw, meta):
    """Valida originales y conserva IDs FotMob separados de API-Football."""
    if hashlib.sha256(raw).hexdigest() != meta["sha256"]:
        raise ValueError("raw_hash_mismatch")
    payload = json.loads(raw)
    norm = normalize_match(fixture, payload, meta["captured_at"])
    captured = timestamp(meta["captured_at"])
    kickoff = timestamp(norm["kickoff_utc"])
    if not kickoff <= captured <= datetime.now(timezone.utc):
        raise ValueError("invalid_capture_time")
    sid = str(norm["fotmob_match_id"])
    if not sid.isdigit() or len(raw) > 16_000_000:
        raise ValueError("invalid_source_id_or_size")
    general, header = payload["general"], payload["header"]
    goals = {}
    for side, index in (("home", 0), ("away", 1)):
        value = header["teams"][index]["score"]
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < 100:
            raise ValueError("invalid_final_score")
        goals[side] = value
    row = {
        "provider": "fotmob", "source_match_id": sid, "league_id": norm["league_id"],
        "season": norm["season"], "kickoff_utc": kickoff.isoformat(),
        "captured_at": captured.isoformat(), "raw_sha256": meta["sha256"],
        "home_source_team_id": norm["home_team_id"], "away_source_team_id": norm["away_team_id"],
        "home_name": general["homeTeam"]["name"], "away_name": general["awayTeam"]["name"],
        "home_goals": goals["home"], "away_goals": goals["away"],
        "home_xg": norm["home_xg"], "away_xg": norm["away_xg"],
        "statistics": json.loads(norm["stats_json"]),
        "counts": {k: norm.get(k) for k in ("home_shots", "away_shots", "home_shots_target",
                                             "away_shots_target", "home_corners", "away_corners")},
        "lineups": [], "players": [], "absences": [],
    }
    content = payload.get("content") or {}
    lineup = content.get("lineup") or {}
    starter_ids = {}
    for side in ("home", "away"):
        team = lineup.get(side + "Team") or {}
        if str(team.get("id")) != row[side + "_source_team_id"]:
            continue
        starters = team.get("starters") or []
        ids = [p.get("id") for p in starters]
        complete = (len(ids) == 11 and len(set(ids)) == 11
                    and all(isinstance(pid, int) and not isinstance(pid, bool) and pid > 0 for pid in ids))
        starter_ids[side] = set(ids)
        row["lineups"].append({"side": side, "formation": team.get("formation"),
                               "complete": complete, "starters": starters,
                               "substitutes": team.get("subs") or []})
        for player in team.get("unavailable") or []:
            if player.get("id") and player.get("name"):
                row["absences"].append({"side": side, "source_player_id": int(player["id"]),
                                        "player_name": player["name"],
                                        "availability": player.get("unavailability") or {}})
    player_stats = content.get("playerStats") or {}
    seen = set()
    for player in player_stats.values() if isinstance(player_stats, dict) else []:
        tid = str(player.get("teamId"))
        side = next((s for s in ("home", "away") if tid == row[s + "_source_team_id"]), None)
        pid = player.get("id")
        if side is None or not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0 or not player.get("name"):
            continue
        if pid in seen:
            raise ValueError("duplicate_player_id")
        seen.add(pid)
        minutes = None
        for group in player.get("stats") or []:
            for stat in (group.get("stats") or {}).values():
                if stat.get("key") == "minutes_played":
                    minutes = number((stat.get("stat") or {}).get("value"))
        row["players"].append({"side": side, "source_player_id": pid,
                                "player_name": player["name"], "minutes": minutes,
                                "starter": pid in starter_ids[side] if side in starter_ids else None,
                                "statistics": player.get("stats") or []})
    return row


def normalize_archive(archive, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    cache = output / "normalized.jsonl.gz"
    if cache.exists():
        raise ValueError("normalized_output_exists")
    errors, counts = [], Counter()
    with gzip.open(cache, "wt", encoding="utf-8") as handle:
        for i, path in enumerate(sorted((Path(archive) / "rows").glob("*.json")), 1):
            fixture = json.loads(path.read_text(encoding="utf-8"))
            sid = str(fixture["fotmob_match_id"])
            try:
                if not sid.isdigit():
                    raise ValueError("invalid_source_id")
                raw_path = Path(archive) / "raw/matches" / (sid + ".json.gz")
                raw = gzip.decompress(raw_path.read_bytes())
                meta = json.loads(raw_path.with_suffix(raw_path.suffix + ".meta.json").read_text())
                record = parse_payload(fixture, raw, meta)
                handle.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
                counts[record["league_id"]] += 1
            except (ValueError, KeyError, TypeError, OSError) as exc:
                errors.append({"source_match_id": sid, "reason": str(exc), "type": type(exc).__name__})
            if i % 2000 == 0:
                print(json.dumps({"processed": i, "valid": sum(counts.values())}), flush=True)
    result = {"valid": sum(counts.values()), "by_league": dict(counts), "errors": errors,
              "normalized_sha256": hashlib.sha256(cache.read_bytes()).hexdigest()}
    json_write(output / "normalization-report.json", result)
    return result


def records(path):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            yield json.loads(line)


class Matcher:
    """Identidades exactas por país; el calendario corrobora nombres e IDs."""
    def __init__(self, snapshot, rows, overrides=None):
        self.teams = {t["team_id"]: t for t in snapshot["teams"]}
        self.leagues = {l["league_id"]: l for l in snapshot["leagues"]}
        self.names = defaultdict(set)
        for team in snapshot["teams"]:
            for name in (team["canonical_name"], team.get("display_name")):
                if name:
                    self.names[slugify(name)].add(team["team_id"])
        for alias in snapshot["aliases"]:
            self.names[slugify(alias["alias"])].add(alias["team_id"])
        self.events = defaultdict(list)
        for m in snapshot["matches"]:
            m = dict(m, kickoff=timestamp(m["kickoff_utc"]))
            self.events[m["league_id"]].append(m)
        self.candidates = {}
        self.reasons = {}
        self.profiles = defaultdict(set)
        self.profile_names = defaultdict(Counter)
        for r in rows:
            for side in ("home", "away"):
                key = (r["league_id"], r[side + "_source_team_id"])
                name = r[side + "_name"]
                self.profile_names[key][name] += 1
                ids = set(self.names.get(slugify(name), set()))
                if not self.leagues[r["league_id"]]["cross_league"]:
                    country = r["league_id"].split(".")[0]
                    ids = {tid for tid in ids if self.teams[tid]["league_id"].split(".")[0] == country}
                self.profiles[key].update(ids)
        for key, ids in self.profiles.items():
            self.candidates[key] = set(ids)
            self.reasons[key] = "exact_name_or_registered_alias"
        for key, decision in (overrides or {}).items():
            league, sid = key.split("/", 1)
            if (league, sid) not in self.profile_names:
                raise ValueError("unknown_override_profile")
            if isinstance(decision, int):
                team = self.teams[decision]
                if not self.leagues[league]["cross_league"] and team["league_id"].split(".")[0] != league.split(".")[0]:
                    raise ValueError("override_wrong_country")
                self.candidates[(league, sid)] = {decision}
            elif isinstance(decision, dict) and decision.get("create"):
                if self.leagues[league]["cross_league"]:
                    raise ValueError("cannot_create_cup_team")
                self.candidates[(league, sid)] = {"new:" + league + ":" + sid}
            else:
                raise ValueError("invalid_override")
            self.reasons[(league, sid)] = "reviewed_override"
        self.overrides = overrides or {}
        # Multiple independent fixtures can corroborate an otherwise unknown name.
        for _ in range(4):
            evidence = defaultdict(lambda: defaultdict(set))
            for r in rows:
                home, away = self.ids(r, "home"), self.ids(r, "away")
                for side, own, other in (("home", home, away), ("away", away, home)):
                    if own or len(other) != 1:
                        continue
                    found = [m for m in self.near(r) if self.score_agrees(r, m)
                             and m[("away" if side == "home" else "home") + "_team_id"] in other]
                    if len(found) == 1:
                        key = (r["league_id"], r[side + "_source_team_id"])
                        evidence[key][found[0][side + "_team_id"]].add(found[0]["match_id"])
            changes = 0
            for key, votes in evidence.items():
                if len(votes) == 1 and len(next(iter(votes.values()))) >= 3:
                    self.candidates[key] = set(votes)
                    self.reasons[key] = "three_corroborating_fixtures"
                    changes += 1
            if not changes:
                break
        # Cups can reuse source IDs identified in domestic fixtures, never create clubs.
        known_by_source = defaultdict(set)
        for (league, sid), ids in self.candidates.items():
            if not self.leagues[league]["cross_league"]:
                known_by_source[sid].update(ids)
        for key, ids in self.candidates.items():
            if self.leagues[key[0]]["cross_league"] and not ids and known_by_source[key[1]]:
                self.candidates[key] = set(known_by_source[key[1]])
                self.reasons[key] = "domestic_source_id"

    def ids(self, r, side):
        return self.candidates[(r["league_id"], r[side + "_source_team_id"])]

    def near(self, r):
        kickoff = timestamp(r["kickoff_utc"])
        return [m for m in self.events[r["league_id"]] if abs(m["kickoff"] - kickoff) <= TOLERANCE]

    @staticmethod
    def score_agrees(r, m):
        return m["status"] == "finished" and all(r[s + "_goals"] == m[s + "_goals"] for s in ("home", "away"))

    def match(self, r):
        home, away = self.ids(r, "home"), self.ids(r, "away")
        near = self.near(r)
        pair = [m for m in near if m["home_team_id"] in home and m["away_team_id"] in away]
        if len(pair) == 1:
            m = pair[0]
            if not self.score_agrees(r, m):
                return {"mapping_status": "conflict", "mapping_reason": "score_or_status_conflict", "match_id": None}
            existing = (m.get("external_ids") or {}).get("fotmob")
            if existing is not None and str(existing) != r["source_match_id"]:
                return {"mapping_status": "conflict", "mapping_reason": "different_source_id", "match_id": None}
            return {"mapping_status": "matched", "mapping_reason": "exact_teams_time_score",
                    "match_id": m["match_id"], "home_team_id": m["home_team_id"], "away_team_id": m["away_team_id"]}
        if pair:
            return {"mapping_status": "conflict", "mapping_reason": "multiple_candidate_matches", "match_id": None}
        if len(home) == len(away) == 1 and home != away:
            # Do not create a duplicate if one identified team already plays nearby.
            clashes = [m for m in near if {m["home_team_id"], m["away_team_id"]} & (home | away)]
            if clashes:
                return {"mapping_status": "conflict", "mapping_reason": "nearby_opponent_conflict", "match_id": None}
            return {"mapping_status": "created", "mapping_reason": "resolved_teams_missing_match",
                    "match_id": "fotmob:" + r["source_match_id"],
                    "home_team_id": next(iter(home)), "away_team_id": next(iter(away))}
        return {"mapping_status": "unresolved", "mapping_reason": "team_identity_unresolved", "match_id": None}


def plan(normalized, snapshot_path, output, overrides_path=None):
    snapshot = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
    # Matching needs only small metadata, not the player/stat payloads.
    metadata = [{k: v for k, v in r.items() if k not in ("players", "lineups", "absences", "statistics", "counts")}
                for r in records(normalized)]
    overrides = json.loads(Path(overrides_path).read_text()) if overrides_path else {}
    matcher = Matcher(snapshot, metadata, overrides)
    decisions, totals, by_league = {}, Counter(), defaultdict(Counter)
    used = defaultdict(list)
    for r in metadata:
        d = matcher.match(r)
        decisions[r["source_match_id"]] = d
        if d["match_id"]:
            used[d["match_id"]].append(r["source_match_id"])
    for mids in used.values():
        if len(mids) > 1:
            for mid in mids:
                decisions[mid] = {"mapping_status": "conflict", "mapping_reason": "duplicate_canonical_target", "match_id": None}
    for r in metadata:
        status = decisions[r["source_match_id"]]["mapping_status"]
        totals[status] += 1
        by_league[r["league_id"]][status] += 1
    profiles = []
    for key, names in matcher.profile_names.items():
        ids = matcher.candidates[key]
        if len(ids) != 1:
            profiles.append({"key": key[0] + "/" + key[1], "names": dict(names),
                             "candidate_ids": sorted(ids, key=str),
                             "candidate_names": [matcher.teams[t]["canonical_name"] for t in ids if isinstance(t, int)]})
    result = {"provider": "fotmob", "decisions": decisions, "totals": dict(totals),
              "by_league": dict(by_league), "unresolved_profiles": profiles, "overrides": overrides,
              "snapshot_sha256": hashlib.sha256(Path(snapshot_path).read_bytes()).hexdigest(),
              "normalized_sha256": hashlib.sha256(Path(normalized).read_bytes()).hexdigest(),
              "new_teams": {"new:" + k.replace("/", ":", 1): {"league_id": k.split("/")[0], "canonical_name": v["create"]}
                            for k, v in overrides.items() if isinstance(v, dict)}}
    json_write(output, result)
    return {"totals": result["totals"], "by_league": result["by_league"], "unresolved_profiles": profiles}


PARENT_COLUMNS = "provider source_match_id league_id season kickoff_utc captured_at raw_sha256 raw_payload_gzip raw_metadata home_source_team_id away_source_team_id home_name away_name home_goals away_goals home_xg away_xg statistics match_id mapping_status mapping_reason".split()
COUNTS = "home_shots away_shots home_shots_target away_shots_target home_corners away_corners".split()
CHILD_COLUMNS = {
    "lineups": "provider source_match_id side formation complete starters substitutes".split(),
    "player_stats": "provider source_match_id side source_player_id player_name minutes starter statistics".split(),
    "absences": "provider source_match_id side source_player_id player_name availability".split(),
}


def apply_import(connection, normalized, plan_path, archive, output, *, rollback=False):
    """Carga atómica e idempotente; los conflictos nunca cambian el partido canónico.

    El original se congela por hash. Un reintento no sobreescribe observaciones
    ni vuelve a crear partidos. rollback permite comprobar las mismas escrituras.
    """
    from psycopg.types.json import Jsonb
    from psycopg import sql
    reviewed = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    digest = hashlib.sha256(Path(normalized).read_bytes()).hexdigest()
    if digest != reviewed["normalized_sha256"]:
        raise ValueError("reviewed_input_hash_changed")
    report = {"normalized_sha256": digest,
              "plan_sha256": hashlib.sha256(Path(plan_path).read_bytes()).hexdigest(),
              "started_at": datetime.now(timezone.utc).isoformat(), "rollback": rollback}
    with connection.transaction():
        connection.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK_ID,))
        connection.execute("SET LOCAL lock_timeout='15s'")
        new_ids = {}
        report["new_team_ids"] = {}
        for ref, team in reviewed.get("new_teams", {}).items():
            league = team["league_id"]
            l = connection.execute("SELECT cross_league FROM leagues WHERE league_id=%s", (league,)).fetchone()
            if not l or l["cross_league"]:
                raise ValueError("cannot_create_cup_team")
            # Resolve a reattempt or a new exact identity added since the review.
            candidates = connection.execute("""SELECT team_id,canonical_name,display_name FROM teams
                WHERE split_part(league_id,'.',1)=%s""", (league.split(".")[0],)).fetchall()
            name = team["canonical_name"]
            found = [t["team_id"] for t in candidates
                     if slugify(name) in {slugify(t["canonical_name"]), slugify(t["display_name"] or "")}]
            if len(found) > 1:
                raise ValueError("ambiguous_reviewed_new_team:" + ref)
            if found:
                tid = found[0]
            else:
                tid = connection.execute("""INSERT INTO teams(league_id,canonical_name,display_name)
                    VALUES(%s,%s,%s) RETURNING team_id""", (league, name, name)).fetchone()["team_id"]
                report["new_team_ids"][ref] = tid
            new_ids[ref] = tid
        for suffix in ("matches", *CHILD_COLUMNS):
            connection.execute(sql.SQL("CREATE TEMP TABLE {} (LIKE {} INCLUDING DEFAULTS) ON COMMIT DROP").format(
                sql.Identifier("stage_" + suffix), sql.Identifier("historical_football_" + suffix)))
        connection.execute("ALTER TABLE stage_matches ADD home_team_id bigint, ADD away_team_id bigint")
        for column in COUNTS:
            connection.execute(sql.SQL("ALTER TABLE stage_matches ADD {} smallint").format(sql.Identifier(column)))
        count = 0
        columns = PARENT_COLUMNS + ["home_team_id", "away_team_id"] + COUNTS
        with connection.cursor().copy(sql.SQL("COPY stage_matches ({}) FROM STDIN").format(
                sql.SQL(",").join(map(sql.Identifier, columns)))) as cp:
            for r in records(normalized):
                sid = r["source_match_id"]
                decision = reviewed["decisions"][sid]
                raw_path = Path(archive) / "raw/matches" / (sid + ".json.gz")
                raw_gzip = raw_path.read_bytes()
                meta = json.loads(raw_path.with_suffix(raw_path.suffix + ".meta.json").read_text())
                if (hashlib.sha256(gzip.decompress(raw_gzip)).hexdigest() != r["raw_sha256"]
                        or meta["sha256"] != r["raw_sha256"]
                        or timestamp(meta["captured_at"]) != timestamp(r["captured_at"])):
                    raise ValueError("original_changed:" + sid)
                row = dict(r, **decision, raw_payload_gzip=raw_gzip, raw_metadata=meta)
                for side in ("home", "away"):
                    key = side + "_team_id"
                    if isinstance(row.get(key), str):
                        row[key] = new_ids[row[key]]
                row["statistics"] = Jsonb(row["statistics"])
                row["raw_metadata"] = Jsonb(meta)
                values = [row.get(k) for k in columns[:len(PARENT_COLUMNS) + 2]]
                for k in COUNTS:
                    value = r["counts"].get(k)
                    values.append(int(value) if value is not None and value == int(value) and 0 <= value < 32768 else None)
                cp.write_row(values)
                count += 1
                if count % 2000 == 0:
                    print(json.dumps({"stage": "originals", "records": count}), flush=True)
        report["originals_staged"] = count
        connection.execute("CREATE UNIQUE INDEX ON stage_matches(provider,source_match_id)")
        for suffix, cols in CHILD_COLUMNS.items():
            field = "players" if suffix == "player_stats" else suffix
            count = 0
            with connection.cursor().copy(sql.SQL("COPY {} ({}) FROM STDIN").format(
                    sql.Identifier("stage_" + suffix), sql.SQL(",").join(map(sql.Identifier, cols)))) as cp:
                for r in records(normalized):
                    for child in r[field]:
                        row = dict(child, provider="fotmob", source_match_id=r["source_match_id"])
                        for k in ("statistics", "availability", "starters", "substitutes"):
                            if k in row:
                                row[k] = Jsonb(row[k])
                        cp.write_row([row.get(k) for k in cols])
                        count += 1
            report[suffix + "_staged"] = count
            print(json.dumps({"stage": suffix, "records": count}), flush=True)
        mismatch = connection.execute("""SELECT s.source_match_id FROM stage_matches s
            JOIN historical_football_matches h USING(provider,source_match_id)
            WHERE s.raw_sha256<>h.raw_sha256 OR s.captured_at<>h.captured_at LIMIT 1""").fetchone()
        if mismatch:
            raise ValueError("frozen_original_conflict:" + str(mismatch))
        # A repeated import must preserve its first identity decision, too.
        connection.execute("""UPDATE stage_matches s SET match_id=h.match_id,
            mapping_status=h.mapping_status,mapping_reason=h.mapping_reason
            FROM historical_football_matches h WHERE s.provider=h.provider AND s.source_match_id=h.source_match_id""")
        connection.execute("""SELECT m.match_id FROM matches m JOIN stage_matches s ON s.match_id=m.match_id FOR UPDATE OF m""")
        connection.execute("""UPDATE stage_matches s SET match_id=NULL,mapping_status='conflict',
            mapping_reason='database_changed_after_review'
            WHERE s.mapping_status='matched' AND NOT EXISTS (
                SELECT 1 FROM matches m WHERE m.match_id=s.match_id AND m.league_id=s.league_id
                AND m.home_team_id=s.home_team_id AND m.away_team_id=s.away_team_id
                AND abs(extract(epoch FROM (m.kickoff_utc-s.kickoff_utc)))<=129600
                AND m.status='finished' AND m.home_goals=s.home_goals AND m.away_goals=s.away_goals
                AND (m.external_ids->>'fotmob' IS NULL OR m.external_ids->>'fotmob'=s.source_match_id))""")
        # New fixtures cannot collide with an existing game, including swapped sides.
        connection.execute("""UPDATE stage_matches s SET match_id=NULL,mapping_status='conflict',
            mapping_reason='nearby_database_match'
            WHERE s.mapping_status='created' AND EXISTS (
                SELECT 1 FROM matches m WHERE m.match_id<>s.match_id AND m.league_id=s.league_id
                AND abs(extract(epoch FROM (m.kickoff_utc-s.kickoff_utc)))<=129600
                AND (m.home_team_id IN (s.home_team_id,s.away_team_id)
                    OR m.away_team_id IN (s.home_team_id,s.away_team_id)))""")
        # Corroborated teams must also be distinct and of the domestic country.
        bad = connection.execute("""SELECT s.source_match_id FROM stage_matches s
            JOIN leagues l USING(league_id)
            LEFT JOIN teams h ON h.team_id=s.home_team_id LEFT JOIN teams a ON a.team_id=s.away_team_id
            WHERE s.match_id IS NOT NULL AND (h.team_id IS NULL OR a.team_id IS NULL OR h.team_id=a.team_id
             OR (NOT l.cross_league AND (split_part(h.league_id,'.',1)<>split_part(s.league_id,'.',1)
                  OR split_part(a.league_id,'.',1)<>split_part(s.league_id,'.',1)))) LIMIT 1""").fetchone()
        if bad:
            raise ValueError("invalid_team_identity:" + str(bad))
        report["canonical_created"] = connection.execute("""INSERT INTO matches
            (match_id,league_id,season,kickoff_utc,home_team_id,away_team_id,status,
             home_goals,away_goals,result_recorded_at,external_ids)
            SELECT match_id,league_id,season,kickoff_utc,home_team_id,away_team_id,'finished',
             home_goals,away_goals,captured_at,jsonb_build_object('fotmob',source_match_id)
            FROM stage_matches WHERE mapping_status='created' ON CONFLICT(match_id) DO NOTHING""").rowcount
        report["xg_added"] = connection.execute("""UPDATE matches m SET home_xg=s.home_xg,
            away_xg=s.away_xg,xg_source='fotmob',xg_recorded_at=s.captured_at
            FROM stage_matches s WHERE m.match_id=s.match_id
            AND m.home_xg IS NULL AND m.away_xg IS NULL AND s.home_xg IS NOT NULL AND s.away_xg IS NOT NULL
            AND m.status='finished' AND m.home_team_id=s.home_team_id AND m.away_team_id=s.away_team_id
            AND m.home_goals=s.home_goals AND m.away_goals=s.away_goals""").rowcount
        report["external_ids_added"] = connection.execute("""UPDATE matches m SET
            external_ids=m.external_ids||jsonb_build_object('fotmob',s.source_match_id)
            FROM stage_matches s WHERE m.match_id=s.match_id AND m.external_ids->>'fotmob' IS NULL""").rowcount
        set_counts = sql.SQL(",").join(sql.SQL("{}=coalesce(m.{},s.{})").format(
            sql.Identifier(k), sql.Identifier(k), sql.Identifier(k)) for k in COUNTS)
        needs_counts = sql.SQL(" OR ").join(sql.SQL("(m.{} IS NULL AND s.{} IS NOT NULL)").format(
            sql.Identifier(k), sql.Identifier(k)) for k in COUNTS)
        report["statistics_enriched"] = connection.execute(sql.SQL("UPDATE matches m SET {} FROM stage_matches s WHERE m.match_id=s.match_id AND ({})").format(set_counts, needs_counts)).rowcount
        for suffix, cols in [("matches", PARENT_COLUMNS), *CHILD_COLUMNS.items()]:
            names = sql.SQL(",").join(map(sql.Identifier, cols))
            report[suffix + "_inserted"] = connection.execute(sql.SQL(
                "INSERT INTO {} ({}) SELECT {} FROM {} ON CONFLICT DO NOTHING").format(
                    sql.Identifier("historical_football_" + suffix), names, names,
                    sql.Identifier("stage_" + suffix))).rowcount
        report["mapping_counts"] = connection.execute("""SELECT league_id,mapping_status,count(*) AS n,
            count(*) FILTER(WHERE home_xg IS NOT NULL AND away_xg IS NOT NULL) AS xg
            FROM stage_matches GROUP BY league_id,mapping_status ORDER BY league_id,mapping_status""").fetchall()
        # Explicit cleanup also makes repeated calls inside one outer test
        # transaction possible; ON COMMIT DROP only fires at the outer commit.
        for suffix in ("matches", *CHILD_COLUMNS):
            connection.execute(sql.SQL("DROP TABLE {}").format(sql.Identifier("stage_" + suffix)))
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        if rollback:
            from psycopg import Rollback
            raise Rollback()
    json_write(output, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    normalize = commands.add_parser("normalize")
    normalize.add_argument("--archive", required=True)
    normalize.add_argument("--output", required=True)
    planner = commands.add_parser("plan")
    planner.add_argument("--normalized", required=True)
    planner.add_argument("--snapshot", required=True)
    planner.add_argument("--output", required=True)
    planner.add_argument("--overrides")
    applier = commands.add_parser("apply")
    applier.add_argument("--normalized", required=True)
    applier.add_argument("--plan", required=True)
    applier.add_argument("--archive", required=True)
    applier.add_argument("--output", required=True)
    applier.add_argument("--rollback", action="store_true")
    args = parser.parse_args()
    if args.command == "normalize":
        result = normalize_archive(args.archive, args.output)
    elif args.command == "plan":
        result = plan(args.normalized, args.snapshot, args.output, args.overrides)
    else:
        from ..db import conn
        with conn() as c:
            result = apply_import(c, args.normalized, args.plan, args.archive, args.output, rollback=args.rollback)
    print(json.dumps(result, ensure_ascii=True), flush=True)


if __name__ == "__main__":
    main()
