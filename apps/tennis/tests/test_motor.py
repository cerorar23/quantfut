import pytest
from tennis_engine.scoring import Rules
from tennis_markets_v2.catalog import Contract
from tennis_motor import devig, recentre


def test_devig_removes_margin_and_rejects_bad_odds():
    assert devig(1.8, 2.1) == pytest.approx((1/1.8)/((1/1.8)+(1/2.1)))
    assert devig(2.0, 2.0) == pytest.approx(.5)
    with pytest.raises(ValueError):
        devig(1.0, 3.0)


def test_recentred_mixture_hits_market_winner_and_keeps_markets_normalized():
    engine = recentre(.66, .62, Rules(3), .2, .70)
    assert engine.probabilities(Contract('winner', 'A'))['win'] == pytest.approx(.70, abs=1e-9)
    total = engine.probabilities(Contract('games_total', 'over', 22.5))
    assert sum(total.values()) == pytest.approx(1)
