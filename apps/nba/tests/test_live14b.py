"""Live 1.4 data variant: RUN071 rows take the new box-score columns without adding or changing anything else."""
import pytest

from nba import live14b_data as data


def row(game, player, team, **extra):
    return dict(game_id=game, player_id=player, team_id=team, season='2024-25', season_type='regular',
                points=10, rebounds=5, assists=2, threes=1, steals=1, blocks=0, **extra)


def test_rows_take_the_columns_of_the_same_game_player_and_team_and_missing_ones_stay_none():
    base = [row('g1', 1, 10), row('g2', 1, 10)]
    extra = [row('g1', 1, 10, tov=3, fga=12, fta=4, oreb=1, pf=2), row('g1', 1, 11, tov=9, fga=9, fta=9, oreb=9)]
    first, second = data.enrich_players(base, extra)
    assert (first['tov'], first['fga'], first['fta'], first['oreb']) == (3, 12, 4, 1) and 'pf' not in first
    assert all(second[k] is None for k in data.COLUMNS) and len(data.enrich_players(base, extra)) == len(base)


def test_a_row_that_disagrees_on_a_count_stops_the_build():
    with pytest.raises(ValueError, match='disagrees'):
        data.enrich_players([row('g1', 1, 10)], [dict(row('g1', 1, 10, tov=1, fga=1, fta=1, oreb=1), points=11)])


def test_games_take_the_possessions_of_each_side():
    side = lambda team, points, **k: dict(team_id=team, points=points, **k)
    base = [dict(game_id='g1', home=side(1, 100), away=side(2, 90)), dict(game_id='g2', home=side(1, 100), away=side(2, 90))]
    extra = [dict(game_id='g1', home=side(1, 100, possessions_estimate=99.5), away=side(2, 90, possessions_estimate=97.))]
    g1, g2 = data.enrich_games(base, extra)
    assert (g1['home']['possessions_estimate'], g1['away']['possessions_estimate']) == (99.5, 97.)
    assert g2['home']['possessions_estimate'] is None and 'possessions_estimate' not in base[0]['home']
    with pytest.raises(ValueError, match='disagrees'):
        data.enrich_games(base, [dict(extra[0], away=side(2, 91))])
