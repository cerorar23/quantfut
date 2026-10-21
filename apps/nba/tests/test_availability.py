from datetime import datetime, timedelta, timezone

import pytest

from nba import availability as av

TIP = datetime(2025, 1, 10, 0, 0, tzinfo=timezone.utc)


def report(minutes_before, status, game='g1', player=7, team=10):
    stamp = TIP - timedelta(minutes=minutes_before)
    return dict(report_timestamp_utc=stamp.isoformat(), rows=[dict(
        nba_game_id=game, nba_player_id=player, status_raw=status, nba_team_id=team, game_tipoff_utc=None)])


def test_report_inside_the_last_hour_is_ignored_and_latest_valid_wins():
    reports = [report(300, 'Questionable'), report(120, 'Out'), report(59, 'Available'), report(60, 'Probable')]
    statuses, observed = av.status_map(reports, {'g1': TIP})
    assert statuses[('g1', '7')][0] == 'Probable' and observed == {'g1'}
    late_only, observed = av.status_map([report(30, 'Out')], {'g1': TIP})
    assert late_only == {} and observed == set()


def test_game_without_known_tipoff_is_unobserved_not_available():
    statuses, observed = av.status_map([report(300, 'Out', game='g2')], {'g1': TIP})
    assert statuses == {} and observed == set()


def test_row_tipoff_is_used_when_the_api_has_none():
    r = report(300, 'Out', game='g3')
    r['rows'][0]['game_tipoff_utc'] = TIP.isoformat()
    statuses, observed = av.status_map([r], {})
    assert statuses[('g3', '7')][0] == 'Out' and 'g3' in observed


def test_unknown_status_label_is_dropped():
    statuses, _ = av.status_map([report(300, 'Rumor')], {'g1': TIP})
    assert statuses == {}


def test_trailing_value_never_uses_the_target_day_or_later():
    games = [dict(game_id=f'g{i}', date=f'2025-01-{i:02d}', season='2024-25',
                  home=dict(team_id=10), away=dict(team_id=20)) for i in range(1, 12)]
    players = [dict(date=g['date'], player_id=7, team_id=10, minutes=30 if g['game_id'] != 'g11' else 480,
                    points=20 if g['game_id'] != 'g11' else 900, participated=True) for g in games]
    statuses = {('g11', '7'): ('Out', 10)}
    got = av.trailing_entries(players, games, statuses, {'g11'})
    (player, status, minutes, points), = got['g11'][10]
    assert (player, status, minutes, points) == ('7', 'Out', 30.0, 20.0)


def test_play_table_is_smoothed_and_expected_missing_follows_it():
    statuses = {('g1', '1'): ('Out', 1), ('g1', '2'): ('Questionable', 1)}
    index = {('g1', '2'): dict(participated=True, minutes=20)}
    table = av.play_table(statuses, index, {'g1'})
    assert table['Out'] == pytest.approx(1 / 3) and table['Questionable'] == pytest.approx(2 / 3)
    minutes, points = av.missing([('1', 'Out', 30., 20.)], table)
    assert minutes == pytest.approx(20.) and points == pytest.approx(40 / 3)
