import numpy as np
import pytest

from nba import multimarket_v15 as v15


class FakeArm:
    def __init__(self, statuses, index):
        self.statuses, self.index = statuses, index


def test_participation_logloss_uses_each_arms_own_status_and_only_the_given_rows():
    index = {('g1', '1'): dict(participated=True, minutes=20), ('g1', '2'): dict(participated=False, minutes=0),
             ('g1', '3'): dict(participated=True, minutes=10)}
    arm = FakeArm({('g1', '1'): ('Probable', 1), ('g1', '2'): ('Out', 1), ('g1', '3'): ('Out', 1)}, index)
    table = {'Probable': .9, 'Out': .1}
    got = v15.participation(arm, [('g1', '1'), ('g1', '2')], table)
    assert got['n'] == 2 and got['logloss'] == pytest.approx(-(np.log(.9) + np.log(.9)) / 2)
    worse = v15.participation(arm, [('g1', '3')], table)  # an Out who played costs a lot
    assert worse['logloss'] == pytest.approx(-np.log(.1))


def test_season_setup_trains_the_table_only_on_the_seasons_before_the_target():
    seasons = ['2021-22', '2022-23', '2023-24', '2024-25']
    index = {('a', '1'): dict(participated=True, minutes=30), ('b', '1'): dict(participated=False, minutes=0),
             ('c', '1'): dict(participated=True, minutes=30)}
    arm = FakeArm({('a', '1'): ('Out', 1), ('b', '1'): ('Out', 1), ('c', '1'): ('Out', 1)}, index)
    arm.observed = {'a', 'b', 'c'}
    game_season = {'a': '2022-23', 'b': '2023-24', 'c': '2024-25'}
    protocol = dict(burn_in_season='2021-22', test_seasons=['2024-25'])
    start, end, train_seasons, table = v15.season_setup('2024-25', seasons, protocol, game_season, arm)
    assert train_seasons == ['2022-23', '2023-24'] and (start, end) == ('2022-08-01', '2024-08-01')
    assert table['Out'] == pytest.approx(2 / 4)  # Beta(1,1): one play + one no-play among two Out rows; game c is the target season
