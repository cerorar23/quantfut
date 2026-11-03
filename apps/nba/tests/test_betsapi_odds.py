import gzip
import json

import pytest

from nba import betsapi_odds as bo

TIP = 1_700_000_000


def row(i, dt, handicap=None, p1='1.909', p2='1.909', ss=None, time_str=None, kind='spread'):
    fields = ('over_od', 'under_od') if kind == 'total' else ('home_od', 'away_od')
    r = {'id': str(i), 'add_time': str(TIP + dt), fields[0]: p1, fields[1]: p2, 'ss': ss, 'time_str': time_str}
    if handicap is not None:
        r['handicap'] = handicap
    return r


def test_only_strict_pregame_valid_rows_become_snapshots():
    rows = [row(1, -900, '-6.5'), row(2, -600, '-7.0', ss='0:0', time_str='1 - 12:00'), row(3, -300, '-7.0', ss='12:11', time_str='1 - 10:00'),
            row(4, -200, '-7.5', p1='-', p2='-'), row(5, -100, '+999'), row(6, 0, '-9.0'), row(7, 60, '-9.5'),
            row(8, -50, '-8.0', p1='1.05', p2='1.05')]
    snaps = bo.snapshots(rows, 'spread', TIP)
    assert [(TIP - s['t'], s['line']) for s in snaps] == [(900, -6.5), (600, -7.0)]


def test_most_balanced_alternate_line_is_the_main_line_and_ties_go_to_the_larger_id():
    rows = [row(1, -100, '-6.5', '1.500', '2.600'), row(2, -100, '-7.5', '1.869', '1.952'), row(3, -100, '-8.5', '2.200', '1.650'),
            row(4, -50, '-7.5', '1.909', '1.909'), row(5, -50, '-8.0', '1.909', '1.909')]
    snaps = bo.snapshots(rows, 'spread', TIP)
    assert [s['line'] for s in snaps] == [-7.5, -8.0]


def test_moneyline_has_no_line_and_total_uses_over_under():
    ml = bo.snapshots([row(1, -10, p1='1.400', p2='3.100')], 'moneyline', TIP)
    assert ml == [dict(t=TIP - 10, line=None, p1=1.4, p2=3.1)]
    tot = bo.snapshots([row(1, -10, '224.5', kind='total')], 'total', TIP)
    assert tot[0]['line'] == 224.5


def test_outcomes_and_pushes():
    assert bo.outcome('moneyline', None, 100, 99) == 1 and bo.outcome('moneyline', None, 20, 20) is None
    assert bo.outcome('spread', -6.5, 110, 100) == 1 and bo.outcome('spread', -6.5, 105, 100) == 0
    assert bo.outcome('spread', 5.0, 95, 100) is None and bo.outcome('spread', 1.5, 99, 100) == 1
    assert bo.outcome('total', 220.5, 111, 110) == 1 and bo.outcome('total', 221.0, 111, 110) is None
    assert bo.outcome('total', 222.5, 111, 110) == 0


def test_novig_and_overround():
    assert bo.novig(2.0, 2.0) == pytest.approx(.5) and bo.overround(2.0, 2.0) == pytest.approx(0)
    assert bo.novig(1.5, 3.0) == pytest.approx(2 / 3)


def scores(q1=(30, 25), q2=(28, 30), h1=(58, 55), q3=(20, 20), q4=(22, 21), total=(100, 96)):
    keys = {'1': q1, '2': q2, '3': h1, '4': q3, '5': q4, '7': total}
    return {k: dict(home=str(v[0]), away=str(v[1])) for k, v in keys.items()}


def test_periods_settles_the_half_only_when_it_adds_up():
    ok = bo.periods(scores())
    assert ok == dict(q1=(30, 25), h1=(58, 55), game=(100, 96))
    assert bo.periods(scores(), swapped=True) == dict(q1=(25, 30), h1=(55, 58), game=(96, 100))
    assert bo.periods(scores(h1=(57, 55)))['h1'] is None


def test_orient_swaps_prices_and_flips_only_the_spread_line():
    s = dict(t=1, line=-6.5, p1=1.5, p2=2.6)
    assert bo.orient(s, 'spread') == dict(t=1, line=6.5, p1=2.6, p2=1.5)
    assert str(bo.orient(dict(t=1, line=0.0, p1=1.5, p2=2.6), 'spread')['line']) == '0.0'
    assert bo.orient(s, 'total') is s


GAMES = [dict(game_id='0022400001', date='2024-10-22', season='2024-25', season_type='regular',
              home=dict(team_id=1, name='Los Angeles Lakers', points=100), away=dict(team_id=2, name='Miami Heat', points=96)),
         dict(game_id='0022400002', date='2024-10-22', season='2024-25', season_type='regular',
              home=dict(team_id=3, name='LA Clippers', points=90), away=dict(team_id=4, name='Portland Trail Blazers', points=80))]


def test_team_names_resolve_by_nickname_and_must_be_unique():
    resolve = bo.team_resolver(GAMES)
    assert [resolve(n) for n in ('LA Lakers', 'MIA Heat', 'LA Clippers', 'POR Trail Blazers')] == [1, 2, 3, 4]
    with pytest.raises(ValueError):
        resolve('XXX Bulls')


def write_event(folder, eid, home, away, tip, ss, rows, status='3'):
    event = dict(event=dict(id=str(eid), time=str(tip), time_status=status, home=dict(name=home), away=dict(name=away),
                            ss=f'{ss["7"]["home"]}-{ss["7"]["away"]}' if ss else None, scores=ss),
                 odds=dict(odds=rows))
    with gzip.open(folder / 'odds' / f'{eid}.json.gz', 'wt', encoding='utf8') as f:
        f.write(json.dumps(event))


def test_build_joins_settles_and_reports_unmatched(tmp_path):
    (tmp_path / 'raw' / 'odds').mkdir(parents=True)
    out = tmp_path / 'out'
    out.mkdir()
    tip = 1_729_650_000  # 2024-10-23 02:20Z -> 2024-10-22 Eastern
    ml = [dict(id='1', add_time=str(tip - 600), home_od='1.800', away_od='2.000', ss=None, time_str=None)]
    sp = [dict(id='2', add_time=str(tip - 600), home_od='1.909', away_od='1.909', handicap='-3.5', ss=None, time_str=None),
          dict(id='3', add_time=str(tip - 60), home_od='1.909', away_od='1.909', handicap='-4.5', ss=None, time_str=None)]
    # BetsAPI lists the visitors first: official home is Lakers (100-96), so the file's 'home' is Miami with 96-100
    write_event(tmp_path / 'raw', 11, 'MIA Heat', 'LA Lakers', tip,
                scores(q1=(25, 30), q2=(30, 28), h1=(55, 58), q3=(20, 20), q4=(21, 22), total=(96, 100)), {'18_1': ml, '18_2': sp})
    write_event(tmp_path / 'raw', 12, 'POR Trail Blazers', 'LA Clippers', tip, scores(total=(80, 91)), {'18_1': ml})  # points differ
    write_event(tmp_path / 'raw', 13, 'MIA Heat', 'LA Clippers', tip, scores(), {'18_1': ml})  # no such pairing
    write_event(tmp_path / 'raw', 15, 'MIA Heat', 'LA Lakers', tip + 400 * 86400, scores(), {'18_1': ml})  # after the reference
    write_event(tmp_path / 'raw', 14, 'LA Lakers', 'MIA Heat', tip, None, {}, status='4')
    ref = tmp_path / 'games.json'
    ref.write_text(json.dumps(GAMES))
    report = bo.build(tmp_path / 'raw', ref, dict(version='t'), out)
    assert report['matched_games'] == 1 and report['unmatched'] == dict(
        points_mismatch=1, no_reference_game=1, postponed_no_scores=1, after_reference_period=1)
    assert report['orientation'] == dict(swapped=1) and report['identity_checked'] == 2 and report['identity_rate'] == .5
    assert report['accepted'] is False and report['events_with_scores'] == 4
    rows = [json.loads(line) for line in gzip.open(out / 'odds.jsonl.gz', 'rt')]
    by = {r['market']: r for r in rows}
    assert set(by) == {'ml_game', 'spread_game'}
    # the file's first-listed price (1.800, Miami) becomes the official away price
    assert by['ml_game']['close']['p1'] == 2.0 and by['ml_game']['close']['p2'] == 1.8 and by['ml_game']['y_close'] == 1
    assert by['ml_game']['close']['seconds_before_tip'] == 600 and by['ml_game']['home_team_id'] == 1
    spread = by['spread_game']
    # Miami -3.5 in the file is the official home +3.5; the Lakers won by 4, so home covers +3.5 and +4.5
    assert spread['open']['line'] == 3.5 and spread['close']['line'] == 4.5 and spread['n_snapshots'] == 2
    assert spread['y_open'] == 1 and spread['y_close'] == 1 and (spread['home_points'], spread['away_points']) == (100, 96)
    assert spread['path'] == [[600, 3.5, 1.909, 1.909], [60, 4.5, 1.909, 1.909]] and spread['close_fresh'] is True
