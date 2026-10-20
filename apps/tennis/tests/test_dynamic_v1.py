"""Artificial matches only."""
import pandas as pd
from tennis_dynamic_v1 import estimated_days, replay, MARGIN_DAYS


def frame():
    base = dict(circuit='ATP', tourney_level='250', surface='Hard', completed_standard=True, period='2026-01-05', tourney_date='20260105', tourney_id='t1')
    rounds = [('R32', 'a', 'b', '6-1 6-1'), ('QF', 'a', 'c', '6-4 6-4'), ('SF', 'a', 'd', '7-5 7-5'), ('F', 'a', 'e', '6-3 6-3')]
    return pd.DataFrame([dict(base, round=r, winner_id=w, loser_id=l, score=s, match_id=f'm{i}', source_row=i) for i, (r, w, l, s) in enumerate(rounds)])


def test_rounds_are_ordered_and_final_is_last_day():
    d = estimated_days(frame())
    assert list(d) == sorted(d) and (d.iloc[-1] - d.iloc[0]).days == 6


def test_no_result_within_margin_leaks_into_a_prediction():
    feats, state = replay(frame(), 'ATP', '2026-01-01')
    days = estimated_days(frame())
    # the R32 result is two or more days before the SF only if the gap allows it; the final never sees itself
    assert feats.loc['m0', 'dyn_p'] == 0.5
    gap_qf = (days.iloc[1] - days.iloc[0]).days
    assert (feats.loc['m1', 'dyn_p'] > .5) == (gap_qf >= MARGIN_DAYS)
    assert state.n['a'] == 4 and state.overall['a'] > 1500


def test_retirement_counts_as_workload_not_rating():
    f = frame().iloc[:1].assign(completed_standard=False, score='6-1 2-0 RET')
    _, state = replay(f, 'ATP', '2026-01-01')
    assert state.overall['a'] == 1500 and state.last['a'] is not None
