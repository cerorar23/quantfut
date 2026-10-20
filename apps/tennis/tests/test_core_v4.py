"""Artificial serve probabilities only: no real players, odds or provider requests."""
import pytest
from tennis_core_v4 import build
from tennis_engine.scoring import Rules
from tennis_allmarkets_v1.contracts import forecast_board, validate_mass
from tennis_markets_v2.catalog import MarketEngine, Contract

PARAMS = dict(k=.9, sigma=.2, w_markov=.34, w_elo=.63)


def winner(engine):
    return engine.probabilities(Contract('winner', 'A'))['win']


def test_final_winner_equals_logit_blend_target_and_board_is_normalized():
    engine = build(.66, .62, .55, Rules(3), PARAMS)
    d = engine.diagnostics
    assert winner(engine) == pytest.approx(d['final_winner'], abs=1e-9)
    assert min(d['markov_winner'], d['elo_winner']) - .05 < d['final_winner'] < max(d['markov_winner'], d['elo_winner']) + .05
    for row in forecast_board(engine):
        validate_mass(row['probabilities'])


def test_overdispersion_pulls_extreme_markov_toward_the_middle_and_adds_straight_sets():
    plain = MarketEngine(.70, .58, Rules(3))
    mixed = build(.70, .58, winner(plain), Rules(3), dict(k=1., sigma=.25, w_markov=0., w_elo=1.))
    assert abs(winner(mixed) - winner(plain)) < 1e-6  # centre re-solved to the requested winner
    straight = lambda e: e.probabilities(Contract('sets_total', 'over', 2.5))['loss']
    assert straight(mixed) > straight(plain)
    total = lambda e: e.probabilities(Contract('games_total', 'over', 22.5))['win']
    assert total(mixed) < total(plain)


def test_symmetry_and_best_of_five_period_mass():
    a = build(.65, .60, .52, Rules(3), PARAMS)
    b = build(.60, .65, .48, Rules(3), PARAMS)
    assert winner(a) == pytest.approx(1 - winner(b), abs=1e-9)
    five = build(.65, .60, .52, Rules(5, deciding_tiebreak=10), PARAMS)
    win, push, loss = (five.probabilities(Contract('set_winner', 'A', set_number=5))[k] for k in ('win', 'push', 'loss'))
    assert win + push + loss == pytest.approx(1) and push > .4


def test_invalid_elo_is_rejected():
    with pytest.raises(ValueError):
        build(.65, .60, 1.0, Rules(3), PARAMS)
