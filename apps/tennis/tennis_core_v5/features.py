"""Pre-match rank, rank points and age from the frozen canonical table; never uses rows after the decision date."""
import math
import pandas as pd

MAX_STALE_DAYS = 60
AGE_RANGE = (14, 50)


def _side(df, pid):
    out = []
    for side, other in (('winner', 'loser'), ('loser', 'winner')):
        sel = df[df[side + '_id'].eq(pid)]
        out.append(pd.DataFrame({'date': pd.to_datetime(sel.tourney_date.astype(str), format='%Y%m%d'), 'order': sel.source_row.to_numpy(),
            'rank': sel[side + '_rank'], 'points': sel[side + '_rank_points'], 'age': sel[side + '_age']}))
    return pd.concat(out)


def latest(df, circuit, pid, as_of):
    day = pd.Timestamp(as_of).tz_localize(None).normalize() if pd.Timestamp(as_of).tzinfo else pd.Timestamp(as_of).normalize()
    rows = _side(df[df.circuit.eq(circuit)], pid)
    rows = rows[(rows.date < day) & rows['rank'].notna() & rows.points.notna() & rows.age.between(*AGE_RANGE)]
    if rows.empty:
        raise ValueError('No usable rank/points/age before the decision date: ' + pid)
    row = rows.sort_values(['date', 'order']).iloc[-1]
    if (day - row.date).days > MAX_STALE_DAYS:
        raise ValueError('Latest rank evidence is stale: ' + pid)
    if row['rank'] < 1:
        raise ValueError('Invalid rank')
    return dict(rank=float(row['rank']), points=float(row.points), age=float(row.age) + (day - row.date).days / 365.25)


def pair_features(df, circuit, a, b, as_of):
    x, y = latest(df, circuit, a, as_of), latest(df, circuit, b, as_of)
    return dict(lrank=math.log(y['rank'] / x['rank']), lpts=math.log((x['points'] + 1) / (y['points'] + 1)), age=(x['age'] - y['age']) / 10)
