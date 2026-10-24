import numpy as np
from scipy.special import expit, logit

from nba import props_market as pm


def quote(**kw):
    base = dict(game_id='g1', player_id=1, market='player_points', line=20.5, over=1.9, under=1.9, actual=25,
                participated=True, minutes=30., minutes_to_tipoff=35.)
    return base | kw


def test_units_average_books_in_logit_space_and_drop_voids_pushes_and_bad_prices():
    rows = [quote(over=1.8, under=2.0), quote(over=2.0, under=1.8), quote(player_id=2, actual=None, participated=None),
            quote(player_id=3, actual=20.5 + 0, line=20.0), quote(player_id=4, over=1.0), quote(player_id=5, over=1.2, under=1.2)]
    out, drops = pm.units(rows)
    assert [(u['player_id'], u['books'], u['y']) for u in out] == [(1, 2, 1), (3, 1, 1)]
    assert abs(out[0]['market_p'] - .5) < 1e-9
    assert drops == dict(no_outcome_or_dnp=1, bad_price=1, overround_out_of_range=1)


def test_push_is_dropped():
    out, drops = pm.units([quote(actual=20, line=20.0)])
    assert out == [] and drops == dict(push=1)


def rows_with_signal(weight, n=6000, seed=1):
    rng = np.random.default_rng(seed)
    lk = rng.normal(0, 1, n)
    extra = rng.normal(0, 1, n)
    truth = expit(lk + weight * extra)
    lm = lk + extra  # model sees the extra signal
    y = (rng.random(n) < truth).astype(int)
    return [dict(model_p=float(expit(a)), market_p=float(expit(b)), y=int(t), date=f'2025-01-{i % 28 + 1:02d}', books=3)
            for i, (a, b, t) in enumerate(zip(lm, lk, y))]


def test_information_weight_recovers_the_signal_and_is_zero_when_model_is_noise():
    informative = pm.information_weight(rows_with_signal(1.0))
    assert .8 < informative['c'] < 1.2 and informative['ci95'][0] > 0
    noise = pm.information_weight(rows_with_signal(0.0))
    assert abs(noise['c']) < .3


def test_blend_endpoints_are_the_market_and_the_model():
    rows = rows_with_signal(1.0, n=50)
    assert np.allclose(pm.blend(rows, 0), [r['market_p'] for r in rows])
    assert np.allclose(pm.blend(rows, 1), [r['model_p'] for r in rows], atol=1e-6)
    assert np.allclose(logit(pm.blend(rows, .5)), (logit([r['model_p'] for r in rows]) + logit([r['market_p'] for r in rows])) / 2, atol=1e-6)
