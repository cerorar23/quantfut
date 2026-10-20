import pandas as pd
from tennis_identity_v3 import resolve


def row(td, w, wn, wage, l, ln, lage, tid):
    return dict(circuit='WTA', period=td[:4] + '-' + td[4:6] + '-' + td[6:], tourney_id=tid, tourney_date=td, winner_id=w, winner_name=wn,
                winner_ioc=None, winner_hand=None, winner_age=wage, loser_id=l, loser_name=ln, loser_ioc=None, loser_hand=None, loser_age=lage)


def test_same_birth_date_merges_and_far_birth_date_is_confirmed_distinct():
    rows = [row('20250105', 'x1', 'Ana Paz', 20.0, 'o1', 'Opp', 30, 't1'), row('20250205', 'x1', 'Ana Paz', 20.085, 'o2', 'Opp B', 30, 't2'),
            row('20250305', 'x2', 'Ana Paz', 20.16, 'o3', 'Opp C', 30, 't3'),  # same person, other ID
            row('20250405', 'y1', 'Eva Sol', 20.0, 'o4', 'Opp D', 30, 't4'), row('20250505', 'y1', 'Eva Sol', 20.1, 'o5', 'Opp E', 30, 't5'),
            row('20250605', 'y2', 'Eva Sol', 35.0, 'o6', 'Opp F', 30, 't6')]  # namesake 15 years older
    merged, distinct, unresolved = resolve(pd.DataFrame(rows))
    assert set(merged) == {'x2'} and merged['x2']['base'] == 'x1'
    assert [d['id'] for d in distinct] == ['y2'] and not unresolved
