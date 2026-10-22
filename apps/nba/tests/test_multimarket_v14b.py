import numpy as np
import pytest

from nba import multimarket_v14b as b


def test_floor_clips_both_ends_and_leaves_the_middle():
    table = b.floored({'Out': 0.0, 'Doubtful': 0.025, 'Questionable': 0.5, 'Probable': 1.0})
    assert table == {'Out': .02, 'Doubtful': .025, 'Questionable': .5, 'Probable': .98}


def row(**extra):
    base = dict(game_id='g1', home_team=10, away_team=20, b2b_home=0, b2b_away=1, elo_gap_mov=50.)
    return dict(base, **extra)


def test_attach_keeps_the_absolute_and_relative_terms_apart():
    table = {'Out': .0, 'Questionable': .5}
    entries = {'g1': {10: [('1', 'Out', 30., 20., 0.0), ('2', 'Out', 20., 10., 1.0)], 20: []}}
    rows = [row()]
    b.attach(rows, entries, table)
    r = rows[0]
    assert (r['mp_home'], r['rp_home']) == (30., 10.)  # absolute counts both; relative only the fresh absence
    assert (r['mm_home'], r['rm_home']) == (50., 20.)
    assert (r['mp_away'], r['rp_away'], r['observed']) == (0., 0., 1)


def test_unobserved_game_contributes_zero_in_both_terms():
    rows = [row(game_id='g9')]
    b.attach(rows, {}, {'Out': 0.})
    r = rows[0]
    assert (r['observed'], r['mp_home'], r['rp_home'], r['mp_away'], r['rp_away']) == (0, 0., 0., 0., 0.)


@pytest.mark.parametrize('spec,width', [(dict(abs=True, rel=False), 6), (dict(abs=True, rel=True), 8), (dict(abs=False, rel=True), 6)])
def test_design_matrices_match_the_declared_terms(spec, width):
    rows = [row(mp_home=10., mp_away=0., rp_home=5., rp_away=0.)]
    assert b.winner_x(rows, spec).shape == (1, width)
    assert b.shift_x(rows, 'home', spec).shape == (1, 3 + 2 * (spec['abs'] + spec['rel']))


def test_absolute_only_design_is_exactly_the_v13_design():
    from nba import multimarket_v13 as v13
    rows = [row(mp_home=10., mp_away=2., rp_home=5., rp_away=1.)]
    spec = dict(abs=True, rel=False)
    assert np.array_equal(b.winner_x(rows, spec), v13.winner_x(rows))
    for side in ('home', 'away'):
        assert np.array_equal(b.shift_x(rows, side, spec), v13.shift_x(rows, side))
