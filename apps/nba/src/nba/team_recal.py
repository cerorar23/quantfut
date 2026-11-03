"""Team points and game total: season-start prior on the form and recalibration (nba_live15_protocol.json).

P  — form entries from an earlier season are regressed toward that season's league mean and the last days of a season are
     left out (apply_prior, on top of the rows of multimarket_v12.team_games; the reference lines never change).
R1 — per-market logistic recalibration fitted on the previous season (fit_recal).
R2 — in-season intercept on top of R1 with a normal prior of scale tau (in_season_intercept).
"""
from collections import defaultdict
from datetime import date

import numpy as np
from scipy.optimize import minimize_scalar
from scipy.special import expit, logit
from scipy.stats import norm

from . import multimarket_v12 as v12

MARKETS = ('team_points', 'game_total')
CLIP = 1e-6


def league_means(games):
    """season -> mean points per team-game over all its games."""
    totals = defaultdict(list)
    for g in games:
        totals[g['season']] += [g['home']['points'], g['away']['points']]
    return {s: float(np.mean(v)) for s, v in totals.items()}


def season_ends(games):
    """season -> last date with a game in that season."""
    out = {}
    for g in games:
        out[g['season']] = max(out.get(g['season'], g['date']), g['date'])
    return out


def team_entries(games):
    """team id -> [(date, season, points, allowed)] in date order."""
    out = defaultdict(list)
    for g in sorted(games, key=lambda g: g['date']):
        for own, other in (('home', 'away'), ('away', 'home')):
            out[g[own]['team_id']].append((g['date'], g['season'], g[own]['points'], g[other]['points']))
    return out


def form(entries, cut, season, protocol, prior, means, ends):
    """(mean points, mean allowed) of the last `history_window` eligible entries strictly before `cut`.

    prior = None reproduces v12.team_games; prior = dict(rho, drop_days) regresses earlier-season entries toward their league
    mean and leaves out those in the last drop_days days of their season (before the window is taken)."""
    today = date.fromisoformat(cut)
    keep = []
    for d, s, pts, alw in entries:
        if d >= cut:
            break
        if prior and s != season:
            if (date.fromisoformat(ends[s]) - date.fromisoformat(d)).days < prior['drop_days']:
                continue
            m = means[s]
            pts, alw = m + (1 - prior['rho']) * (pts - m), m + (1 - prior['rho']) * (alw - m)
        keep.append((d, pts, alw))
    keep = keep[-protocol['history_window']:] if not prior else keep
    keep = [k for k in keep if 0 < (today - date.fromisoformat(k[0])).days <= protocol['history_max_days']]
    keep = keep[-protocol['history_window']:]
    if not keep:
        return None
    return float(np.mean([k[1] for k in keep])), float(np.mean([k[2] for k in keep]))


def apply_prior(rows, games, protocol, prior):
    """Copies of v12.team_games rows with home_mean/away_mean rebuilt from the prior form (same home advantage, same lines).

    `games` must contain every game the rows were built from (only games strictly before each row's date are read)."""
    if not prior:
        return [dict(r) for r in rows]
    entries, means, ends = team_entries(games), league_means(games), season_ends(games)
    out = []
    for r in rows:
        base = [form(entries[r[s + '_team']], r['date'], r['season'], protocol, None, means, ends) for s in ('home', 'away')]
        new = [form(entries[r[s + '_team']], r['date'], r['season'], protocol, prior, means, ends) for s in ('home', 'away')]
        r = dict(r)
        if None not in new:
            raw = lambda f, own, opp: (f[own][0] + f[opp][1]) / 2
            r['home_mean'] = r['home_mean'] - raw(base, 0, 1) + raw(new, 0, 1)
            r['away_mean'] = r['away_mean'] - raw(base, 1, 0) + raw(new, 1, 0)
        out.append(r)
    return out


def units(rows, preds):
    """Scoring units of predict_team output: (market, key, date, line, y, p)."""
    out = []
    for r, p in zip(rows, preds):
        for side in ('home', 'away'):
            q = p[side]
            out.append(dict(market='team_points', key=r['game_id'] + side, date=r['date'], line=q['line'],
                            y=int(r[side + '_points'] > q['line']), p=q['p']))
        q = p['total']
        out.append(dict(market='game_total', key=r['game_id'], date=r['date'], line=q['line'],
                        y=int(r['home_points'] + r['away_points'] > q['line']), p=q['p']))
    return out


def clip_logit(p):
    return logit(np.clip(np.asarray(p, float), CLIP, 1 - CLIP))


def fit_recal(unit_rows):
    """market -> dict(a, b, units): maximum-likelihood logistic recalibration of each market's units."""
    out = {}
    for market in MARKETS:
        sub = [u for u in unit_rows if u['market'] == market]
        z, y = clip_logit([u['p'] for u in sub]), np.array([u['y'] for u in sub], float)
        x = np.column_stack([np.ones(len(z)), z])
        w = v12.fit_ridge_logistic(x, y, np.array([0., 1.]), 0.)
        out[market] = dict(a=float(w[0]), b=float(w[1]), units=len(sub))
    return out


def recal_p_logit(p, recal, market):
    z = clip_logit(p)
    if not recal:
        return z
    r = recal[market]
    return r['a'] + r['b'] * z


def in_season_intercept(z, y, tau):
    """argmax_c sum log-lik(y | expit(z + c)) - c^2 / (2 tau^2); 0 with no earlier unit."""
    z, y = np.asarray(z, float), np.asarray(y, float)
    if not len(z):
        return 0.
    f = lambda c: float(np.sum(np.logaddexp(0, z + c) - y * (z + c)) + c * c / (2 * tau * tau))
    return float(minimize_scalar(f, bounds=(-2, 2), method='bounded', options=dict(xatol=1e-7)).x)


def with_intercepts(unit_rows, earlier_rows, recal, tau):
    """R2: each unit's probability with the intercept fitted on the season's units of earlier dates.

    unit_rows carry the probability to correct (with availability); earlier_rows the same units predicted without availability
    (what the producer can recompute for finished games). Both keyed by (market, key)."""
    early = {(u['market'], u['key']): u for u in earlier_rows}
    out, by_date = [], defaultdict(list)
    for u in unit_rows:
        by_date[u['date']].append(u)
    seen = defaultdict(list)
    for day in sorted(by_date):
        cs = {}
        for market in MARKETS:
            past = seen[market]
            z = [float(recal_p_logit(e['p'], recal, market)) for e in past]
            cs[market] = in_season_intercept(z, [e['y'] for e in past], tau)
        for u in by_date[day]:
            out.append(dict(u, p=float(expit(recal_p_logit(u['p'], recal, u['market']) + cs[u['market']])), intercept=cs[u['market']]))
        for u in by_date[day]:
            e = early.get((u['market'], u['key']))
            if e is not None:
                seen[u['market']].append(e)
    return out


def live_probability(mean, sd, line, market, recal, c=0.):
    """The probability a live forecast publishes: normal tail at the line, then R1 (and R2's intercept c)."""
    p = float(norm.sf(line, mean, sd))
    if not recal:
        return p
    return float(expit(recal_p_logit(p, recal, market) + c))
