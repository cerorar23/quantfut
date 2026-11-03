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


from datetime import UTC, datetime, timedelta

import pytest
from scipy.special import expit, logit

from nba import availability as av

BOOT = dict(bootstrap=200, seed=11)


def synthetic(n=3000, c=.6, seed=5):
    """Outcomes drawn from logit(p) = logit(market) + c * (logit(model) - logit(market))."""
    rng = np.random.default_rng(seed)
    market = np.clip(rng.uniform(.2, .8, n), .05, .95)
    model = np.clip(market + rng.normal(0, .08, n), .03, .97)
    p = expit(logit(market) + c * (logit(model) - logit(market)))
    y = (rng.uniform(size=n) < p).astype(int)
    return [dict(game_id=str(i), date=f'2025-{i % 5 + 1:02d}-{i % 27 + 1:02d}', model=float(m), market=float(k), y=int(o),
                 overround=.04, minutes_to_tipoff=float(30 + (i % 4) * 90)) for i, (m, k, o) in enumerate(zip(model, market, y))]


def test_information_weight_recovers_how_much_the_model_matters():
    for true_c in (0., 1.):
        out = mc.information_weight(synthetic(c=true_c, n=6000), BOOT)
        low, high = out['ci95_date_bootstrap']
        assert low < true_c < high and abs(out['c'] - true_c) < .35


def test_a_model_with_no_information_has_a_weight_interval_that_includes_zero_and_a_useful_one_excludes_it():
    assert mc.information_weight(synthetic(c=0.), BOOT)['ci95_date_bootstrap'][0] <= 0
    assert mc.information_weight(synthetic(c=1., n=6000), BOOT)['ci95_date_bootstrap'][0] > 0


def test_strata_cover_every_game_once():
    rows = synthetic(400)
    out = mc.strata(rows)
    assert sum(b['n'] for b in out['minutes_to_tipoff']) == 400 and sum(b['n'] for b in out['gap']) == 400


def test_aligned_arm_hides_reports_published_after_the_price_was_taken():
    tip = datetime(2025, 1, 15, 0, 30, tzinfo=UTC)
    snapshot = datetime(2025, 1, 14, 19, 0, tzinfo=UTC)

    def report(hour, status):
        return dict(report_timestamp_utc=datetime(2025, 1, 14, hour, 30, tzinfo=UTC).isoformat(), rows=[dict(
            nba_game_id='g1', nba_player_id=7, status_raw=status, nba_team_id=10, game_tipoff_utc=None)])
    reports = [report(14, 'Questionable'), report(21, 'Out')]  # 14:30Z before the price, 21:30Z after it but before tipoff - 60
    tips = {'g1': tip}
    published, _ = av.status_map(reports, tips)
    capped, _ = av.status_map(reports, mc.aligned_tips(tips, [dict(game_id='g1', snapshot_utc=snapshot.isoformat())]))
    assert published[('g1', '7')][0] == 'Out' and capped[('g1', '7')][0] == 'Questionable'
    # a price taken after the usual cutoff changes nothing
    late = mc.aligned_tips(tips, [dict(game_id='g1', snapshot_utc=(tip - timedelta(minutes=10)).isoformat())])
    assert late['g1'] == tip
    assert mc.aligned_tips(tips, [dict(game_id='other', snapshot_utc=snapshot.isoformat())]) == tips


def season_report(coverage=.95, lower=.1, brier_upper=.001, walk=-.001, n=500):
    arm = dict(n=n, model_vs_market=dict(ci95_date_bootstrap=[brier_upper - .01, brier_upper]),
               information_weight=dict(c=.4, ci95_date_bootstrap=[lower, .8]))
    return dict(coverage=coverage, aligned=arm)


def test_decision_rule_has_three_outcomes_and_an_inconclusive_one():
    protocol = dict(seasons=['2024-25', '2025-26'])
    walk = lambda d: dict(blend_vs_market=dict(paired_brier_difference=d))
    informative = dict(seasons={'2024-25': season_report(), '2025-26': season_report()}, walk_forward=walk(-.001))
    assert mc.decide(informative, protocol)['verdict'] == 'adds_information'
    no_walk = dict(informative, walk_forward=walk(.0005))
    assert mc.decide(no_walk, protocol)['verdict'] == 'no_evidence_of_added_information'
    weak = dict(seasons={'2024-25': season_report(lower=-.2), '2025-26': season_report()}, walk_forward=walk(-.001))
    assert mc.decide(weak, protocol)['verdict'] == 'no_evidence_of_added_information'
    better = dict(seasons={s: season_report(brier_upper=-.001) for s in protocol['seasons']}, walk_forward=walk(-.001))
    assert mc.decide(better, protocol)['verdict'] == 'better_than_market'
    thin = dict(seasons={'2024-25': season_report(coverage=.7), '2025-26': season_report()}, walk_forward=walk(-.001))
    assert mc.decide(thin, protocol)['verdict'] == 'inconclusive'


def test_walk_forward_uses_the_first_seasons_weight_and_the_power_devig_sensitivity_is_reported():
    first, second = synthetic(c=.8, n=5000, seed=1), synthetic(c=.8, n=5000, seed=2)
    out = mc.walk_forward(first, second, BOOT)
    assert .5 < out['c_from_first_season'] < 1.1 and out['blend_vs_market']['paired_brier_difference'] < 0
    rows = [dict(r, market_power=r['market']) for r in first[:300]]
    assert 'sensitivity_power_devig' in mc.compare_to_market(rows, BOOT)
    assert 'sensitivity_power_devig' not in mc.compare_to_market(first[:300], BOOT)
