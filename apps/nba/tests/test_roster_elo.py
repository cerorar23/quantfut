from datetime import date, timedelta
import json
from pathlib import Path

import pytest

from nba import multimarket_v12 as v12
from nba import roster_elo as re_

PROTOCOL = json.loads((Path(__file__).parents[1] / 'multimarket_v12_protocol.json').read_bytes())
TEAMS = (1, 2, 3, 4)


def league(seasons=('2023-24', '2024-25'), per_season=24, trade=None):
    """Round-robin games; each team has five players (id = team * 10 + k). trade=(player, new_team, season) moves a player."""
    games, players, n = [], [], 0
    for s_index, season in enumerate(seasons):
        start = date(2023 + s_index, 10, 20)
        for day in range(per_season):
            cut = (start + timedelta(days=2 * day)).isoformat()
            pairs = ((1, 2), (3, 4)) if day % 2 else ((1, 3), (2, 4))
            for home, away in pairs:
                n += 1
                gid = f'002{n:07d}'
                hp, ap = 100 + 3 * (5 - home) + day % 3, 100 + 3 * (5 - away)
                games.append(dict(game_id=gid, date=cut, season=season, home=dict(team_id=home, points=hp),
                                  away=dict(team_id=away, points=ap)))
                for team in (home, away):
                    for k in range(5):
                        pid = team * 10 + k
                        if trade and pid == trade[0] and s_index >= seasons.index(trade[2]):
                            continue
                        players.append(dict(game_id=gid, player_id=pid, team_id=team, minutes=48. - 4 * k,
                                            participated=True, points=20 - 3 * k, rebounds=5, assists=3, tov=1))
                    if trade and team == trade[1] and s_index >= seasons.index(trade[2]):
                        players.append(dict(game_id=gid, player_id=trade[0], team_id=team, minutes=40.,
                                            participated=True, points=25, rebounds=6, assists=4, tov=2))
    return games, players


def test_plain_pass_matches_team_games_and_stayers_are_unchanged():
    games, players = league()
    rows = v12.team_games(games, PROTOCOL)
    assert rows
    for weights in re_.WEIGHTS:
        gaps = re_.effective_gaps(games, players, PROTOCOL, weights, 1.)
        out = re_.apply(rows, gaps)  # raises if the margin Elo pass differs
        assert all(abs(r['elo_gap_mov'] - r['elo_gap_base']) < 1e-9 for r in out)


def test_traded_player_carries_his_old_team_rating():
    games, players = league(trade=(10, 4, '2024-25'))  # team 1's best player moves to team 4 for the second season
    base = re_.effective_gaps(games, players, PROTOCOL, 'minutes', 0.)
    moved = re_.effective_gaps(games, players, PROTOCOL, 'minutes', 1.)
    second = sorted((g for g in games if g['season'] == '2024-25'), key=lambda g: g['date'])
    first_of_4 = next(g for g in second if 4 in (g['home']['team_id'], g['away']['team_id']))
    assert moved[first_of_4['game_id']]['gap'] == pytest.approx(base[first_of_4['game_id']]['gap'])  # no rotation yet
    later = [g for g in second[8:] if 4 in (g['home']['team_id'], g['away']['team_id'])]
    sign = lambda g: 1 if g['home']['team_id'] == 4 else -1
    # team 1 is the strongest, so carrying its rating lifts team 4's effective Elo
    assert all(sign(g) * (moved[g['game_id']]['gap'] - base[g['game_id']]['gap']) > 0 for g in later)
    assert all(base[g['game_id']]['gap'] == base[g['game_id']]['base_gap'] for g in games)


def test_production_weights_give_the_star_a_larger_share():
    games, players = league(trade=(10, 4, '2024-25'))
    base = re_.effective_gaps(games, players, PROTOCOL, 'minutes', 0.)
    by_minutes = re_.effective_gaps(games, players, PROTOCOL, 'minutes', 1.)
    by_production = re_.effective_gaps(games, players, PROTOCOL, 'production', 1.)
    g = [g for g in games if g['season'] == '2024-25' and 4 in (g['home']['team_id'], g['away']['team_id'])][-1]
    lift = lambda gaps: abs(gaps[g['game_id']]['gap'] - base[g['game_id']]['gap'])
    assert lift(by_production) > lift(by_minutes) > 0


def test_only_earlier_dates_are_used():
    games, players = league(trade=(10, 4, '2024-25'))
    cut = sorted({g['date'] for g in games})[-6]
    later = {g['game_id'] for g in games if g['date'] >= cut}
    changed_games = [dict(g, home=dict(g['home'], points=g['home']['points'] + 30)) if g['game_id'] in later else g for g in games]
    changed_players = [dict(r, minutes=1.) if r['game_id'] in later else r for r in players]
    a = re_.effective_gaps(games, players, PROTOCOL, 'production', 1.)
    b = re_.effective_gaps(changed_games, changed_players, PROTOCOL, 'production', 1.)
    on_cut = {g['game_id'] for g in games if g['date'] == cut}
    for g in games:
        if g['date'] < cut or g['game_id'] in on_cut:
            assert a[g['game_id']] == b[g['game_id']]


def test_apply_refuses_a_different_elo_pass():
    games, players = league()
    rows = v12.team_games(games, PROTOCOL)
    gaps = re_.effective_gaps(games, players, PROTOCOL, 'minutes', 1.)
    gaps[rows[0]['game_id']] = dict(gaps[rows[0]['game_id']], base_gap=gaps[rows[0]['game_id']]['base_gap'] + 1)
    with pytest.raises(ValueError):
        re_.apply(rows, gaps)
