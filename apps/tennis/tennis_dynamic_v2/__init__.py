"""Sequential surface-aware Weighted Elo plus workload/inactivity, ordered by estimated round day.

Most source dates are tournament start dates, so each match gets an estimated day: start + its position in the
draw (final at the event's last day, earlier rounds evenly before it, qualifying before the start). Some files
(mostly ATP 2026 and qualifying) carry per-match dates instead: when a tournament has more than one distinct
date, that date is used as the match day without any offset (v1 shifted them, which could leak later results). A match on
estimated day D is predicted only with results whose estimated day is <= D - MARGIN_DAYS, so overlapping
events and two-week tournaments cannot leak later rounds into earlier predictions.
"""
from collections import defaultdict, deque
import math
import numpy as np
import pandas as pd

MARGIN_DAYS = 2
EVENT_DAYS = {'G': 13, 'M': 11, '1000': 11}
DEPTH = {'F': 0, 'BR': 0, 'SF': 1, 'QF': 2, 'R16': 3, 'R32': 4, 'R64': 5, 'R128': 6}
QUAL = {'Q1': -3, 'Q2': -2, 'Q3': -1}
SURFACES = ('Hard', 'Clay', 'Grass', 'Carpet')


def estimated_days(df):
    start = pd.to_datetime(df.tourney_date.astype(str), format='%Y%m%d')
    depth = df['round'].map(DEPTH)
    key = [df.circuit, df.tourney_id]
    per_match = df.tourney_date.groupby(key).transform('nunique') > 1
    deepest = depth.groupby(key).transform('max').fillna(0).clip(lower=1)
    length = df.tourney_level.map(EVENT_DAYS).fillna(6)
    main = start + pd.to_timedelta((length * (1 - depth / deepest)).round(), unit='D')
    qual = start + pd.to_timedelta(df['round'].map(QUAL).fillna(0), unit='D')
    other = start + pd.to_timedelta(2, unit='D')  # round robin / ties: mid-event, conservative margin applies
    weekly = main.where(depth.notna(), qual.where(df['round'].isin(QUAL), other))
    return start.where(per_match, weekly)


def games_share(score):
    won = lost = 0
    for token in str(score).split():
        part = token.split('(')[0]
        if '-' not in part:
            return None
        a, b = part.split('-')
        if not (a.isdigit() and b.isdigit()):
            return None
        won, lost = won + int(a), lost + int(b)
    return won / (won + lost) if won + lost else None


class State:
    def __init__(self):
        self.overall = defaultdict(lambda: 1500.)
        self.surface = defaultdict(lambda: 1500.)
        self.n = defaultdict(int)
        self.n_surface = defaultdict(int)
        self.last = {}
        self.recent = defaultdict(deque)

    @staticmethod
    def k(n):
        return 250 / (n + 5) ** .4

    def prob(self, a, b, surface):
        po = 1 / (1 + 10 ** ((self.overall[b] - self.overall[a]) / 400))
        ps = 1 / (1 + 10 ** ((self.surface[(b, surface)] - self.surface[(a, surface)]) / 400))
        return (po + ps) / 2

    def features(self, a, b, surface, day):
        def side(p):
            gap = (day - self.last[p]).days if p in self.last else 365
            load = sum(1 for d in self.recent[p] if 0 <= (day - d).days <= 14)
            return math.log1p(min(gap, 365)), load, math.log1p(self.n[p])
        sa, sb = side(a), side(b)
        return dict(dyn_p=self.prob(a, b, surface), d_layoff=sa[0] - sb[0], d_load14=sa[1] - sb[1], d_experience=sa[2] - sb[2])

    def update(self, w, l, surface, share, day, completed=True):
        for p in (w, l):
            self.last[p] = day
            self.recent[p].append(day)
            while self.recent[p] and (day - self.recent[p][0]).days > 30:
                self.recent[p].popleft()
        if not completed or share is None:
            return  # retirements count as workload, not as rating evidence
        factor = share
        po = 1 / (1 + 10 ** ((self.overall[l] - self.overall[w]) / 400))
        ps = 1 / (1 + 10 ** ((self.surface[(l, surface)] - self.surface[(w, surface)]) / 400))
        kw, kl = self.k(self.n[w]), self.k(self.n[l])
        ksw, ksl = self.k(self.n_surface[(w, surface)]), self.k(self.n_surface[(l, surface)])
        self.overall[w] += kw * (1 - po) * factor
        self.overall[l] -= kl * (1 - po) * factor
        self.surface[(w, surface)] += ksw * (1 - ps) * factor
        self.surface[(l, surface)] -= ksl * (1 - ps) * factor
        for p in (w, l):
            self.n[p] += 1
            self.n_surface[(p, surface)] += 1


def usable(df, circuit, since):
    x = df[df.circuit.eq(circuit) & df.period.ge(since) & df.surface.isin(SURFACES) & df.winner_id.ne(df.loser_id)].copy()
    x = x[~x.score.astype(str).str.contains('W/O|DEF|walkover', case=False, na=True)]
    x['day'] = estimated_days(x)
    x['completed'] = x.completed_standard.fillna(False).astype(bool)
    return x.sort_values(['day', 'tourney_id', 'source_row'], kind='mergesort')


def replay(df, circuit, since='2000-01-01', until=None):
    """Return pre-match features (winner = A) for every usable match, and the final state."""
    x = usable(df, circuit, since)
    state, pending, out = State(), deque(), []
    for row in x.itertuples():
        if until is not None and row.day >= until:
            break
        while pending and pending[0][0] <= row.day - pd.Timedelta(days=MARGIN_DAYS):
            d, w, l, s, share, done = pending.popleft()
            state.update(w, l, s, share, d, done)
        f = state.features(row.winner_id, row.loser_id, row.surface, row.day)
        out.append(dict(match_id=row.match_id, **f))
        pending.append((row.day, row.winner_id, row.loser_id, row.surface, games_share(row.score), row.completed))
    while pending:
        d, w, l, s, share, done = pending.popleft()
        state.update(w, l, s, share, d, done)
    return pd.DataFrame(out).set_index('match_id'), state


def oriented(features, y):
    """Flip winner-perspective features to the A/B orientation (y=1 means A won)."""
    f = features.copy()
    flip = np.asarray(y) == 0
    f.loc[flip, 'dyn_p'] = 1 - f.loc[flip, 'dyn_p']
    for col in ('d_layoff', 'd_load14', 'd_experience'):
        f.loc[flip, col] = -f.loc[flip, col]
    return f
