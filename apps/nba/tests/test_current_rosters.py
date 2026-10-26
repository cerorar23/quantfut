from datetime import UTC, datetime, timedelta
import hashlib
import json

import pytest

from nba import current_rosters as cr
from nba import multimarket_v13_live as live
from nba.audit import digest

NOW = datetime(2026, 10, 26, 21, tzinfo=UTC)
TEAM = 1610612749


def page(tid=TEAM, ids=range(1, 7), season='2026-27'):
    team = dict(id=tid, info=dict(TEAM_ID=tid, SEASON_YEAR=season), scheduleSeason=season,
                roster=[dict(PLAYER_ID=p, PLAYER=f'Player {p}', TeamID=tid, SEASON=season[:4], LeagueID='00') for p in ids])
    return ('<script id="__NEXT_DATA__">' + json.dumps(dict(props=dict(pageProps=dict(team=team)))) + '</script>').encode()


def receipt(raw, tid=TEAM, received=NOW):
    return dict(url=f'https://www.nba.com/team/{tid}/{cr.TEAM_SLUGS[tid]}', http_status=200,
                raw_sha256=hashlib.sha256(raw).hexdigest(), raw_file=f'{tid}.html', first_received_at_utc=received.isoformat())


def test_current_official_roster_uses_ids_and_keeps_real_receipt():
    raw = page()
    rows = cr.parse(raw, receipt(raw), '2026-27')
    assert rows[0]['team_id'] == TEAM and rows[0]['player_id'] == 1
    assert rows[0]['first_received_at_utc'] == NOW.isoformat()
    snapshot = dict(season='2026-27', teams=[TEAM], players=rows)
    assert cr.membership(snapshot, NOW, '2026-27', [TEAM])['1'] == TEAM
    for at in (NOW - timedelta(seconds=1), NOW + cr.TTL + timedelta(seconds=1)):
        with pytest.raises(ValueError, match='late or stale'):
            cr.membership(snapshot, at, '2026-27', [TEAM])


@pytest.mark.parametrize('raw,season', [(page(season='2025-26'), '2026-27'), (page(ids=[1] * 6), '2026-27'),
                                     (page(ids=range(1, 5)), '2026-27')])
def test_stale_duplicate_or_incomplete_roster_rejected(raw, season):
    with pytest.raises(ValueError):
        cr.parse(raw, receipt(raw), season)


def test_cross_team_duplicate_and_missing_team_rejected():
    rows = cr.parse(page(), receipt(page()), '2026-27')
    snapshot = dict(season='2026-27', teams=[TEAM, TEAM + 1], players=rows + [dict(r, team_id=TEAM + 1) for r in rows])
    with pytest.raises(ValueError, match='conflicting'):
        cr.membership(snapshot, NOW, '2026-27', [TEAM, TEAM + 1])
    snapshot['players'] = rows
    with pytest.raises(ValueError, match='incomplete'):
        cr.membership(snapshot, NOW, '2026-27', [TEAM, TEAM + 1])


def test_capture_cache_preserves_receipt_and_verifies_raw_bytes(tmp_path):
    calls = []
    get = lambda url: (calls.append(url) or (200, page()))
    first = cr.capture([TEAM], '2026-27', tmp_path / 'one', get, lambda: NOW, tmp_path / 'cache')
    second = cr.capture([TEAM], '2026-27', tmp_path / 'two', get, lambda: NOW + timedelta(minutes=10), tmp_path / 'cache')
    assert first == second and len(calls) == 1
    folder = tmp_path / 'two'
    assert cr.verify(folder, digest(folder / 'snapshot.json'), NOW + timedelta(minutes=10), '2026-27', [TEAM])['1'] == TEAM
    (folder / f'{TEAM}.html').write_bytes(b'tampered')
    with pytest.raises(ValueError, match='raw bytes changed'):
        cr.verify(folder, digest(folder / 'snapshot.json'), NOW + timedelta(minutes=10), '2026-27', [TEAM])
    bad = json.loads((tmp_path / 'cache' / 'rosters' / f'{TEAM}.json').read_bytes())
    bad['receipt']['url'] = 'https://example.org/wrong'
    (tmp_path / 'cache' / 'rosters' / f'{TEAM}.json').write_text(json.dumps(bad))
    with pytest.raises(ValueError, match='cache URL'):
        cr.capture([TEAM], '2026-27', tmp_path / 'three', get, lambda: NOW, tmp_path / 'cache')


def test_transfer_to_opponent_assigns_only_new_team_even_before_debut():
    from test_multimarket_v13_live import V12, mapping, player_rows
    m = mapping()
    history = live.player_history(player_rows())
    # Player 1 last played for HOME; official roster now places him on AWAY. Player 2 has left both teams.
    memberships = {'1': m['away_nba_team_id']}
    model = dict(play_probability=dict.fromkeys(live.av.STATUSES, .5), player_empirical_weight=.25,
                 player_fit={'player_points': dict(weights=[1., 0., 0., 0., 0.])})
    lines = {m['nba_game_id']: {('player_points', 1): dict(line=18.5, books=2, book_lines={})}}
    rows, _ = live.player_forecasts(model, V12, [m], lines, history, {}, roster_since='2026-10-20', memberships=memberships)
    assert len(rows) == 1
    assert rows[0]['team_id'] == m['away_nba_team_id']
    assert rows[0]['transferred'] and rows[0]['membership_source'] == 'official_nba_roster'
    assert rows[0]['last_feature_date'] < '2026-10-20'  # old personal history is portable, membership is current
    rows, _ = live.player_forecasts(model, V12, [m], {}, history, {}, roster_since='2026-10-20', memberships=memberships)
    assert len(rows) == 1 and rows[0]['line_source'] == 'statistical'


def test_quote_cannot_resurrect_a_player_who_left_both_teams():
    from test_multimarket_v13_live import V12, mapping, player_rows
    m = mapping()
    model = dict(play_probability={}, player_empirical_weight=.25,
                 player_fit={'player_points': dict(weights=[1., 0., 0., 0., 0.])})
    rows, summary = live.player_forecasts(model, V12, [m], {m['nba_game_id']: {('player_points', 1):
        dict(line=18.5, books=2, book_lines={})}}, live.player_history(player_rows()), {}, memberships={})
    assert rows == [] and summary[m['nba_game_id']]['not_on_current_roster'] == 1


def test_real_snapshot_round_trip_in_a_sealed_cohort_and_source_tampering(tmp_path, monkeypatch):
    from test_multimarket_v13_live import (HOME, AWAY, DAY, V12, PROTOCOL, model, fake_get, parsed_report,
                                         player_rows, history_games)
    from nba.audit import write_json
    from nba import injury_pdf
    from nba.multimarket_live_dashboard import LiveCohort
    for tid in (HOME, AWAY):
        monkeypatch.setitem(cr.TEAM_SLUGS, tid, 'test-club')
    def get(url):
        if '/team/' in url:
            tid = int(url.split('/')[4])
            return 200, page(tid, range(tid * 10, tid * 10 + 6))
        return fake_get(url)
    now = datetime(2026, 10, 21, 14, 29, tzinfo=UTC)
    monkeypatch.setattr(injury_pdf, 'extract_report', lambda path, url, received: parsed_report(received))
    fitted = model()
    fitted['options'] = dict(official_rosters=True)
    fitted['inputs']['current_rosters_sha256'] = cr.code_digest()
    model_dir = tmp_path / 'model'
    model_dir.mkdir()
    write_json(model_dir / 'model.json', fitted)
    folder = tmp_path / 'cohort'
    live.seal(model_dir, folder, DAY, player_rows(), history_games(), PROTOCOL, V12, now=now, get=get, first_completed_day=DAY)
    board = LiveCohort(folder)
    assert board.bundle['roster']['players'] == 12
    assert board.bundle['games'][0]['availability']['roster_conflicts'] == 1
    (folder / 'rosters' / f'{HOME}.html').write_bytes(b'tampered source')
    with pytest.raises(ValueError, match='raw bytes changed'):
        board.load()
