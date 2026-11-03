from datetime import date, timedelta

import numpy as np
from scipy.special import expit

from nba import live_combos_check as chk
from nba import multimarket_v13_live as live


def rows(n=6000, seed=0):
    rng = np.random.default_rng(seed)
    out, p = [], []
    for i in range(n):
        raw = float(rng.uniform(.1, .9))
        truth = expit(.6 * np.log(raw / (1 - raw)) - .1)  # the raw law is overconfident: true slope 0.6
        out.append(dict(date=(date(2025, 11, 1) + timedelta(days=i % 120)).isoformat(), offset=live.LINE_OFFSETS[i % len(live.LINE_OFFSETS)],
                        y=int(rng.random() < truth)))
        p.append(raw)
    return out, np.array(p)


def test_an_overconfident_raw_law_is_fixed_by_a_calibration_that_undoes_it():
    data, raw = rows()
    live_p = expit(.6 * np.log(raw / (1 - raw)) - .1)  # the fitted calibration, here the true one
    entry = chk.evaluate_market(data, raw, live_p)
    assert entry['live_vs_raw']['paired_brier_difference'] < 0 and entry['live_vs_raw']['interval'][1] < 0
    assert .9 <= entry['live']['slope'] <= 1.1 and entry['raw']['slope'] < .75
    assert entry['enable_in_live'] and set(entry['by_offset']) == {str(o) for o in live.LINE_OFFSETS}


def test_a_calibration_that_does_not_beat_the_raw_law_is_not_enabled():
    data, raw = rows(seed=1)
    entry = chk.evaluate_market(data, raw, raw)  # identical probabilities: no gain
    assert entry['live_vs_raw']['paired_brier_difference'] == 0 and not entry['decision']['beats_raw'] and not entry['enable_in_live']


def test_decision_requires_every_condition():
    good = dict(live=dict(slope=1.0, intercept=.02), live_vs_raw=dict(interval=[-.01, -.002]))
    assert chk.enabled(chk.decide(good))
    assert not chk.enabled(chk.decide(dict(good, live=dict(slope=1.3, intercept=.02))))
    assert not chk.enabled(chk.decide(dict(good, live=dict(slope=1.0, intercept=.3))))
    assert not chk.enabled(chk.decide(dict(good, live_vs_raw=dict(interval=[-.01, .001]))))
