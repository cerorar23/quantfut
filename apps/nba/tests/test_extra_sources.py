import json

import pytest
import httpx

from nba.audit import digest
from nba.extra_sources import (LINEUPS_URL, ROTATIONS_URL, audit_lineups, audit_rotation_game,
    audit_rotations, capture_supplemental, parse_lineups, supplemental_files)


def lineup_html(state="expected", date="2026-10-05", count=5):
    sides = []
    for css, team in (("is-visit", "MEM"), ("is-home", "ATL")):
        players = ''.join(f'<li class="lineup__player"><a href="/basketball/player/name-{i}" title="Player {i}">P {i}</a></li>' for i in range(1, count + 1))
        sides.append(f'<a class="lineup__team {css}"><div class="lineup__abbr">{team}</div></a><ul class="lineup__list {css}"><li class="lineup__status is-{state}"></li>{players}<li class="lineup__title">MAY NOT PLAY</li><li class="lineup__player"><a title="Player 9" href="/basketball/player/name-9">P9</a><span class="lineup__inj">Out</span></li></ul>')
    return f'<main data-sportfull="basketball" data-gamedate="{date}"><div class="lineup is-nba"><div class="lineup__time">7:00 PM ET</div>{"".join(sides)}</div></main>'


def rotation_fixture(overtime=0):
    game = dict(home_team_id="20", away_team_id="30", league="nba", date="2025-10-21", season="2025-26", season_type="Regular Season", stats={}, team_results={})
    box = []
    total_minutes = 48 + 5 * overtime
    for side, tid, pids in (("Home", 20, range(1, 6)), ("Away", 30, range(6, 11))):
        entity = '-'.join(map(str, pids))
        stats, teams = {}, {}
        for p in range(1, 5 + overtime):
            minutes = "12:00" if p <= 4 else "05:00"
            stats[str(p)] = [dict(EntityId=entity, Minutes=minutes, Points=5, OffPoss=3, DefPoss=3)]
            teams[str(p)] = dict(Minutes=minutes, Points=5)
        stats["FullGame"] = [dict(EntityId=entity, Minutes=f"{total_minutes:02d}:00", Points=5 * (4 + overtime))]
        teams["FullGame"] = dict(Minutes=f"{total_minutes:02d}:00", Points=5 * (4 + overtime))
        game["stats"][side], game["team_results"][side] = stats, teams
        for pid in pids:
            box.append(dict(game_id="0022500001", player_id=pid, team_id=tid, season="2025-26", season_type="regular",
                            date="2025-10-21", minutes=total_minutes, points=4 + overtime, participated=True))
    return game, box


def manifest(tmp_path, name, body, url, source, received="2026-10-05T20:00:00+00:00", **extra):
    folder = tmp_path / name.replace('.', '_')
    folder.mkdir()
    path = folder / name
    path.write_text(body, encoding="utf-8")
    meta = dict(source=source, files=[dict(name=name, bytes=path.stat().st_size, sha256=digest(path), url=url,
                                         first_received_at_utc=received)], **extra)
    mp = folder / "manifest.json"
    mp.write_text(json.dumps(meta))
    return mp


def test_expected_vs_confirmed_and_injuries_are_separate():
    game = parse_lineups(lineup_html())[0]
    assert game["away"]["status"] == "expected"
    assert len(game["away"]["starters"]) == 5
    assert game["away"]["may_not_play"][0]["provider_injury_label"] == "Out"
    assert game["away"]["starters"][0]["nba_player_id"] is None
    assert parse_lineups(lineup_html("confirmed"))[0]["home"]["status"] == "confirmed_by_provider"


def test_explicit_advertising_cards_are_excluded():
    html = lineup_html().replace('</main>', '<div class="lineup is-nba is-tools is-picks">Advert</div></main>')
    assert len(parse_lineups(html)) == 1


@pytest.mark.parametrize("html", [lineup_html(count=4), lineup_html(date="invalid"), lineup_html() + lineup_html()])
def test_malformed_or_duplicated_lineups_fail_closed(html):
    with pytest.raises(ValueError):
        parse_lineups(html)


def test_future_lineup_capture_and_date_mismatch(tmp_path):
    lm = manifest(tmp_path, "rotowire.html", lineup_html(), LINEUPS_URL, "RotoWire_public_lineups")
    event = dict(id="7", date="2026-10-05T23:00Z", competitions=[dict(competitors=[
        dict(homeAway="home", team=dict(abbreviation="ATL")), dict(homeAway="away", team=dict(abbreviation="MEM"))])])
    cm = manifest(tmp_path, "scoreboard_20261005.json", json.dumps(dict(events=[event])), "https://site.api.espn.com/",
                  "NBA_ESPN_public_context", date_requested="2026-10-05")
    with pytest.raises(ValueError, match="future"):
        audit_lineups(lm, cm, "2026-10-05T19:00:00Z")
    report = audit_lineups(lm, cm, "2026-10-05T21:00:00Z")
    assert report["games"][0]["candidate_event_id"] == "espn:7"
    assert report["games"][0]["captured_before_candidate_tip"] is True
    assert report["games"][0]["event_link_verified"] is False
    assert report["actionable"] is False
    mp = json.loads(lm.read_text()); raw = lm.parent / "rotowire.html"
    raw.write_text(lineup_html(date="2026-10-06")); mp["files"][0].update(bytes=raw.stat().st_size, sha256=digest(raw)); lm.write_text(json.dumps(mp))
    assert audit_lineups(lm, cm, "2026-10-05T21:00:00Z")["summary"]["candidate_calendar_matches"] == 0


def test_integrity_and_namespaces_enforced(tmp_path):
    lm = manifest(tmp_path, "rotowire.html", lineup_html(), LINEUPS_URL, "RotoWire_public_lineups")
    (lm.parent / "rotowire.html").write_text("changed")
    with pytest.raises(ValueError, match="integrity"):
        supplemental_files(lm)
    with pytest.raises(ValueError, match="IDs"):
        capture_supplemental(tmp_path, ["espn:401898388"])
    with pytest.raises(ValueError, match="unique"):
        capture_supplemental(tmp_path, ["0022500001"] * 21)


@pytest.mark.parametrize("overtime", [0, 2])
def test_clock_conservation_including_overtime(overtime):
    data, rows = rotation_fixture(overtime)
    result = audit_rotation_game(data, "0022500001", rows)
    assert result["periods"] == 4 + overtime
    assert len(result["quarter_lineups"]) == 2 * (4 + overtime)
    assert all(x["error_seconds"] == 0 for x in result["player_exposures"])


@pytest.mark.parametrize("change", ["wrong_player", "clock", "points", "dnp", "box_minutes", "missing_period", "season"])
def test_rotation_faults_quarantine_entire_game(change):
    data, rows = rotation_fixture()
    if change == "wrong_player": data["stats"]["Home"]["1"][0]["EntityId"] = "1-2-3-4-6"
    if change == "clock": data["stats"]["Home"]["1"][0]["Minutes"] = "11:00"
    if change == "points": data["stats"]["Home"]["1"][0]["Points"] = 100
    if change == "dnp": rows[0]["participated"] = False
    if change == "box_minutes": rows[0]["minutes"] = 30
    if change == "missing_period": del data["stats"]["Away"]["3"]
    if change == "season": data["season"] = "2024-25"
    with pytest.raises(ValueError): audit_rotation_game(data, "0022500001", rows)


def test_aggregate_quantization_retained_not_rescaled():
    data, rows = rotation_fixture()
    data["stats"]["Home"]["1"][0]["Minutes"] = "11:59"
    report = audit_rotation_game(data, "0022500001", rows)
    assert report["quarter_lineups"][0]["reported_seconds"] == 719
    assert report["clock_errors"][0]["reported_clock_error_seconds"] == -1


def test_game_url_and_reference_cannot_be_substituted(tmp_path):
    data, rows = rotation_fixture()
    data["stats"]["Home"]["1"][0]["Name"] = "Dončić"
    mp = manifest(tmp_path, "lineup_0022500001.json", json.dumps(data, ensure_ascii=False), ROTATIONS_URL + "?GameId=0022500001&Type=Lineup", "PBPStats_public_game_lineups")
    assert audit_rotations(mp, rows)["summary"]["accepted_games"] == 1
    assert audit_rotations(mp, [])["summary"]["quarantined_games"] == 1
    changed = json.loads(mp.read_text()); changed["files"][0]["url"] = ROTATIONS_URL + "?GameId=0022500002&Type=Lineup"; mp.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="URL identity"):
        audit_rotations(mp, rows)


@pytest.mark.parametrize("status", [403, 429, 503])
def test_public_capture_stops_on_denial_or_server_failure(tmp_path, monkeypatch, status):
    calls = []
    original = httpx.Client
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(status, text="unavailable")
    monkeypatch.setattr("nba.extra_sources.httpx.Client", lambda **kw: original(transport=httpx.MockTransport(handler), **kw))
    result = capture_supplemental(tmp_path, ["0022500001", "0022500002"])
    assert len(calls) == 1
    assert result["files"] == 0
    assert result["errors"][0]["status"] == status
