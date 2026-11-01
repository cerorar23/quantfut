from datetime import datetime, timedelta, timezone

import pytest

from nba import multimarket_v14 as v14

TIP = datetime(2025, 1, 12, 0, 0, tzinfo=timezone.utc)


def row(reason, status='Out', player=7):
    return dict(nba_game_id='g1', nba_player_id=player, status_raw=status, nba_team_id=10, reason_raw=reason, game_tipoff_utc=None)


def report(*rows):
    return dict(report_timestamp_utc=(TIP - timedelta(hours=5)).isoformat(), rows=list(rows))


def test_g_league_rows_get_their_own_category_only_when_asked():
    reports = [report(row('G League - Two-Way'), row('Injury/Illness - Left Ankle; Sprain', player=8))]
    split, _ = v14.status_map(reports, {'g1': TIP}, True)
    plain, _ = v14.status_map(reports, {'g1': TIP}, False)
    assert split[('g1', '7')][0] == 'G League' and split[('g1', '8')][0] == 'Out'
    assert plain[('g1', '7')][0] == 'Out'
    assert split.keys() == plain.keys()


def test_g_league_assignment_is_recognised_with_any_raw_status():
    reports = [report(row('G League - On Assignment', status='Available'))]
    split, _ = v14.status_map(reports, {'g1': TIP}, True)
    assert split[('g1', '7')][0] == 'G League'


def games_and_players(missed_last_ten):
    games = [dict(game_id=f'g{i}', date=f'2025-01-{i:02d}', season='2024-25',
                  home=dict(team_id=10), away=dict(team_id=20)) for i in range(1, 12)]
    players = []
    for g in games[:-1]:
        i = int(g['game_id'][1:])
        players.append(dict(game_id=g['game_id'], date=g['date'], player_id=7, team_id=10, minutes=30, points=20,
                            participated=not (i > 1 and missed_last_ten)))
        # five early games so he clears the minimum history either way
        if not players[-1]['participated']:
            players[-1].update(minutes=0, points=0)
    return games, players


def test_share_played_counts_the_team_games_the_player_took_part_in():
    games, players = games_and_players(missed_last_ten=False)
    for p in players[:6]:
        p['participated'] = True
    entries = v14.trailing_entries(players, games, {('g11', '7'): ('Out', 10)}, {'g11'})
    (player, status, minutes, points, share), = entries['g11'][10]
    assert (status, minutes, points, share) == ('Out', 30.0, 20.0, 1.0)

    games, players = games_and_players(missed_last_ten=True)
    for p in players[:6]:
        p['participated'] = True
        p['minutes'], p['points'] = 30, 20
    entries = v14.trailing_entries(players, games, {('g11', '7'): ('Out', 10)}, {'g11'})
    (_, _, _, _, share), = entries['g11'][10]
    assert share == pytest.approx(0.6)  # played g1-g6 of the team's ten earlier games


def test_share_never_uses_the_target_day():
    games, players = games_and_players(missed_last_ten=False)
    players.append(dict(game_id='g11', date='2025-01-11', player_id=7, team_id=10, minutes=999, points=999, participated=True))
    entries = v14.trailing_entries(players, games, {('g11', '7'): ('Out', 10)}, {'g11'})
    (_, _, minutes, points, share), = entries['g11'][10]
    assert (minutes, points, share) == (30.0, 20.0, 1.0)


def test_relative_missing_is_zero_for_an_absence_already_in_the_form_and_signed_for_returns():
    table = {'Out': 0.0, 'Questionable': 0.5}
    already_out = [('1', 'Out', 30., 20., 0.0)]
    assert v14.missing(already_out, table, True) == (0., 0.)
    assert v14.missing(already_out, table, False) == (30., 20.)
    fresh_out = [('1', 'Out', 30., 20., 1.0)]
    assert v14.missing(fresh_out, table, True) == (30., 20.)
    returning = [('1', 'Questionable', 30., 20., 0.2)]
    minutes, points = v14.missing(returning, table, True)
    assert minutes == pytest.approx(-9.) and points == pytest.approx(-6.)


def test_play_table_has_a_g_league_category():
    statuses = {('g1', '1'): ('G League', 10), ('g1', '2'): ('Out', 10)}
    table = v14.play_table(statuses, {('g1', '2'): dict(participated=False, minutes=0)}, {'g1'})
    assert set(table) == set(v14.CATEGORIES) and table['G League'] == pytest.approx(1 / 3)
