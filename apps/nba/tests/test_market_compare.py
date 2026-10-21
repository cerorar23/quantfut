import numpy as np

from nba import market_compare as mc

PROTOCOL = dict(bootstrap=200, seed=7)


def rows(n=400, seed=1):
    rng = np.random.default_rng(seed)
    truth = rng.uniform(.2, .8, n)
    y = (rng.uniform(size=n) < truth).astype(int)
    return truth, y


def test_join_keeps_only_games_with_a_market_price():
    model = [dict(game_id='a', date='2025-01-01', model=.6, y=1), dict(game_id='b', date='2025-01-01', model=.4, y=0)]
    odds = [dict(game_id='a', home_no_vig=.55, overround=.04, minutes_to_tipoff=30.)]
    joined = mc.join(model, odds)
    assert [r['game_id'] for r in joined] == ['a'] and joined[0]['market'] == .55


def test_a_model_equal_to_the_market_has_zero_difference():
    truth, y = rows()
    data = [dict(game_id=str(i), date=f'2025-01-{i % 28 + 1:02d}', model=float(p), market=float(p), y=int(o),
                 overround=.04, minutes_to_tipoff=30.) for i, (p, o) in enumerate(zip(truth, y))]
    out = mc.compare_to_market(data, PROTOCOL)
    assert out['model_vs_market']['paired_brier_difference'] == 0
    assert abs(out['blend_vs_market']['paired_brier_difference']) < 1e-12


def test_a_noisy_model_loses_to_the_true_market_and_the_interval_says_so():
    truth, y = rows(2000)
    noise = np.random.default_rng(3).normal(0, .15, len(truth))
    model = np.clip(truth + noise, .05, .95)
    data = [dict(game_id=str(i), date=f'2025-{i % 6 + 1:02d}-{i % 28 + 1:02d}', model=float(m), market=float(p), y=int(o),
                 overround=.04, minutes_to_tipoff=30.) for i, (m, p, o) in enumerate(zip(model, truth, y))]
    out = mc.compare_to_market(data, PROTOCOL)['model_vs_market']
    assert out['paired_brier_difference'] > 0 and out['ci95_date_bootstrap'][0] > 0


def test_empty_join_reports_zero_games():
    assert mc.compare_to_market([], PROTOCOL) == dict(n=0)
