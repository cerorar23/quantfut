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


def test_runtime_config_can_live_outside_the_repo(tmp_path, monkeypatch):
    import importlib, tennis_motor
    monkeypatch.setenv('TENNIS_MOTOR_CONFIG', str(tmp_path / 'motor_config.json'))
    module = importlib.reload(tennis_motor)
    assert module.CONFIG == tmp_path / 'motor_config.json'
    monkeypatch.delenv('TENNIS_MOTOR_CONFIG')
    importlib.reload(tennis_motor)


def test_dynamic_features_clamp_estimated_future_round_days():
    import math
    import pandas as pd
    from tennis_dynamic_v2 import State
    from tennis_motor import dynamic_features, board_with_model
    s, day = State(), pd.Timestamp('2026-10-25')
    s.last['a'], s.recent['a'] = pd.Timestamp('2026-10-27'), [pd.Timestamp('2026-10-27')]  # estimated final day of this week
    s.last['b'], s.recent['b'] = pd.Timestamp('2026-10-20'), [pd.Timestamp('2026-10-20')]
    f = dynamic_features(s, 'a', 'b', 'Hard', day)  # the frozen State.features raised "math domain error" here
    assert f['d_layoff'] == pytest.approx(-math.log1p(5)) and f['d_load14'] == 0
    engine = recentre(.66, .62, Rules(3), .2, .70)
    board = dict(rows=[dict(contract=dict(kind='games_handicap', selection='A', line=-2, set_number=None, score=None), market=.5, books=1),
                       dict(contract=dict(kind='sets_total', selection='over', line=3.5, set_number=None, score=None), market=.5, books=1)])
    rows = board_with_model(engine, board)['rows']
    p = engine.probabilities(Contract('games_handicap', 'A', -2))
    assert len(rows) == 1 and rows[0]['model'] == pytest.approx(p['win'] / (1 - p['push']))  # 3.5 sets is not a best-of-3 line


def test_players_without_serve_statistics_are_forecast_not_dropped():
    import pandas as pd
    from tennis_motor import Motor

    class Serve:
        names = {'wta:1': 'Ana Paz'}

        def resolve(self, value):
            if value in self.names:
                return value
            raise ValueError('Player name absent or ambiguous; use a canonical ID: ' + value)
    m = Motor.__new__(Motor)
    m.models, m.names_cache = {'WTA': Serve()}, {}
    m.canonical = pd.DataFrame([dict(circuit='WTA', winner_id='wta:9', winner_name='Xinran Sun', loser_id='wta:1', loser_name='Ana Paz')])
    assert m.resolve('WTA', 'wta:1') == 'wta:1' and m.resolve('WTA', 'wta:9') == 'wta:9'
    assert m.canonical_name('WTA', 'wta:9') == 'Xinran Sun'
    with pytest.raises(ValueError):
        m.resolve('WTA', 'wta:404')
