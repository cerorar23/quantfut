"""Portable individual strength and rotation changes, using strictly earlier completed games.

Game-level ridge coefficients are associations with a player's minutes, not causal on/off or RAPM estimates.
The correction compares the new rotation with the rotation already represented in the team's recent form.
"""
from collections import defaultdict, deque
from datetime import date
import hashlib
from pathlib import Path

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import lsqr
from scipy.special import expit, logit
from scipy.stats import norm

WINDOW, MAX_DAYS, HALF_LIFE = 20, 370, 180


def code_digest():
    return hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def allocate_minutes(weights):
    """240 regulation minutes; no player can take more than 48. Insufficient capacity is an error."""
    weights = {str(p): float(w) for p, w in weights.items() if float(w) > 0}
    if any(not np.isfinite(w) for w in weights.values()) or len(weights) < 5:
        raise ValueError('insufficient finite rotation capacity')
    result, remaining, active = {}, 240., dict(weights)
    while active:
        denominator = sum(active.values())
        capped = [p for p, w in active.items() if remaining * w / denominator >= 48]
        if not capped:
            result.update({p: remaining * w / denominator for p, w in active.items()})
            break
        for p in capped:
            result[p] = 48.
            remaining -= 48.
            del active[p]
    if abs(sum(result.values()) - 240) > 1e-6:
        raise ValueError('rotation minutes do not reconcile')
    return result


def box_minutes(rows, team):
    own = {str(r['player_id']): float(r['minutes']) for r in rows
           if r['team_id'] == team and r['participated'] and r['minutes'] > 0}
    total = sum(own.values())
    if len(own) < 5 or not 239 <= total <= 340:
        raise ValueError('incomplete training rotation')
    return {p: m * 240 / total for p, m in own.items()}


def fit_ratings(games, players, before, ridge=50.):
    """Two seasons of actual rotations before `before`: ridge on margin and total, exponential date weighting.

    A player coefficient follows his official ID through every change of team. No team Elo enters this fit.
    The intercept is unpenalized; every player is shrunk towards the league-average player (coefficient zero).
    """
    if not np.isfinite(ridge) or ridge <= 0:
        raise ValueError('positive finite ridge required')
    cut = date.fromisoformat(before)
    chosen = [g for g in games if 0 < (cut - date.fromisoformat(g['date'])).days <= 730]
    by_id = {g['game_id']: g for g in chosen}
    box = defaultdict(list)
    for r in players:
        if r['game_id'] in by_id:
            if r['date'] != by_id[r['game_id']]['date']:
                raise ValueError('player/game date mismatch')
            box[r['game_id']].append(r)
    rotations, accepted = [], []
    for g in chosen:
        if not box[g['game_id']]:
            continue
        rotations.append([box_minutes(box[g['game_id']], g[s]['team_id']) for s in ('home', 'away')])
        accepted.append(g)
    if len(accepted) < 30:
        raise ValueError('insufficient earlier games for player strength')
    ids = sorted({p for sides in rotations for side in sides for p in side}, key=int)
    index = {p: i for i, p in enumerate(ids)}
    age = np.array([(cut - date.fromisoformat(g['date'])).days for g in accepted])
    weights = 2. ** (-age / HALF_LIFE)
    weights = np.sqrt(weights / weights.mean())
    result = dict(before=before, ridge=float(ridge), half_life_days=HALF_LIFE, games=len(accepted),
                  last_feature_date=max(g['date'] for g in accepted))
    for target, sign in (('margin', -1), ('total', 1)):
        rr, cc, vv = [], [], []
        for i, (home, away) in enumerate(rotations):
            for side, factor in ((home, 1), (away, sign)):
                for p, m in side.items():
                    rr.append(i); cc.append(index[p]); vv.append(factor * m / 48.)
            rr.append(i); cc.append(len(ids)); vv.append(1.)
        x = sparse.coo_matrix((vv, (rr, cc)), shape=(len(accepted), len(ids) + 1)).tocsr()
        y = np.array([g['home']['points'] + sign * g['away']['points'] for g in accepted], float)
        penalty = sparse.diags([np.sqrt(ridge)] * len(ids) + [0.])
        design = sparse.vstack([x.multiply(weights[:, None]), penalty], format='csr')
        solved = lsqr(design, np.r_[weights * y, np.zeros(len(ids) + 1)], atol=1e-8, btol=1e-8, iter_lim=2000)
        if solved[1] not in (1, 2, 4, 5) or not np.all(np.isfinite(solved[0])):
            raise ValueError('player-strength regression did not converge')
        result[target] = dict(intercept=float(solved[0][-1]), weights=dict(zip(ids, map(float, solved[0][:-1]))))
    return result


class RotationHistory:
    def __init__(self):
        self.teams = defaultdict(lambda: deque(maxlen=WINDOW))
        self.players = defaultdict(lambda: deque(maxlen=WINDOW))
        self.last_team = {}

    def observe(self, game, players):
        for side in ('home', 'away'):
            tid = game[side]['team_id']
            minutes = box_minutes(players, tid)
            self.teams[tid].append((game['date'], game['season'], minutes))
        for r in players:
            if r['participated'] and r['minutes'] > 0:
                pid = str(r['player_id'])
                self.players[pid].append((game['date'], r['team_id'], float(r['minutes'])))
                self.last_team[pid] = r['team_id']

    def rotation(self, team, day, season, memberships=None):
        """Current roster or an explicitly limited retrospective approximation from previous appearances."""
        recent = [g for g in self.teams[team] if 0 < (date.fromisoformat(day) - date.fromisoformat(g[0])).days <= MAX_DAYS]
        current = [g for g in recent if g[1] == season][-5:]
        if memberships is None:
            # Without dated historical rosters the first game of a new season is unobservable, not 'unchanged'.
            if not current:
                return None
            roster = {p for g in current for p in g[2] if self.last_team.get(p) == team}
        else:
            roster = {str(p) for p, tid in memberships.items() if tid == team}
        weights = {}
        for p in roster:
            history = [r for r in self.players[p] if 0 < (date.fromisoformat(day) - date.fromisoformat(r[0])).days <= MAX_DAYS]
            prior = np.mean([r[2] for r in history]) if history else 12.
            # New-team minutes increasingly replace the prior role, rather than inheriting the old role forever.
            new = [g[2].get(p, 0.) for g in current]
            weights[p] = (5 * prior + sum(new)) / (5 + len(new))
        if len([w for w in weights.values() if w > 0]) < 5:
            return None
        return allocate_minutes(weights)

    def change(self, team, day, season, ratings, memberships=None):
        if ratings['before'] > day or ratings['last_feature_date'] >= day:
            raise ValueError('player strength was fitted with future games')
        recent = [g for g in self.teams[team] if 0 < (date.fromisoformat(day) - date.fromisoformat(g[0])).days <= MAX_DAYS]
        rotation = self.rotation(team, day, season, memberships)
        if not recent or rotation is None:
            return dict(margin=0., total=0., observed=False, unknown_minutes=0., turnover=0.)
        baseline = defaultdict(float)
        for _, _, played in recent:
            for p, m in played.items():
                baseline[p] += m / len(recent)
        output = dict(observed=True, rotation=rotation,
                      unknown_minutes=sum(m for p, m in rotation.items() if p not in ratings['margin']['weights']),
                      turnover=sum(max(0., m - baseline[p]) for p, m in rotation.items()) / 240.)
        for target in ('margin', 'total'):
            w = ratings[target]['weights']
            output[target] = sum((rotation.get(p, 0.) - baseline[p]) * w.get(p, 0.) / 48
                                 for p in set(rotation) | set(baseline))
        return output


def features(games, players, ridge=50.):
    """Out-of-season individual fits plus chronological rotation features; target-day boxes are observed afterwards."""
    seasons = sorted({g['season'] for g in games})
    ratings = {}
    for season in seasons[1:]:
        ratings[season] = fit_ratings(games, players, season[:4] + '-08-01', ridge)
    by_day, box = defaultdict(list), defaultdict(list)
    for g in games:
        by_day[g['date']].append(g)
    for r in players:
        box[r['game_id']].append(r)
    history, out = RotationHistory(), {}
    for day in sorted(by_day):
        for g in by_day[day]:
            if g['season'] in ratings:
                out[g['game_id']] = {s: history.change(g[s]['team_id'], day, g['season'], ratings[g['season']])
                                     for s in ('home', 'away')}
        for g in by_day[day]:
            history.observe(g, box[g['game_id']])
    return out, ratings


def adjust(prediction, change, covariance, weight):
    """Shift each team's points from individual rotation changes, retaining the calibrated reference variance."""
    if not np.isfinite(weight) or not 0 <= weight <= 1:
        raise ValueError('finite rotation weight in [0, 1] required')
    out = {k: dict(v) if isinstance(v, dict) else v for k, v in prediction.items()}
    dh = weight * (change['home']['total'] + change['home']['margin']) / 2
    da = weight * (change['away']['total'] + change['away']['margin']) / 2
    # Defensive strength: net contribution to the margin is shared symmetrically between own scoring and opponent scoring.
    mh = dh + weight * (change['away']['total'] - change['away']['margin']) / 2
    ma = da + weight * (change['home']['total'] - change['home']['margin']) / 2
    for side, shift in (('home', mh), ('away', ma), ('total', mh + ma)):
        out[side]['mean'] += shift
        out[side]['p'] = float(norm.sf(out[side]['line'], out[side]['mean'], out[side]['sd']))
    sd_margin = np.sqrt(covariance[0][0] + covariance[1][1] - 2 * covariance[0][1])
    base = norm.cdf((prediction['home']['mean'] - prediction['away']['mean']) / sd_margin)
    new = norm.cdf((out['home']['mean'] - out['away']['mean']) / sd_margin)
    out['winner'] = float(expit(logit(np.clip(prediction['winner'], 1e-6, 1 - 1e-6))
                              + logit(np.clip(new, 1e-6, 1 - 1e-6)) - logit(np.clip(base, 1e-6, 1 - 1e-6))))
    return out


def live_changes(games, players, mappings, memberships, ratings):
    cut = min(m['et_date'] for m in mappings)
    box = defaultdict(list)
    for row in players:
        if row['date'] < cut:
            box[row['game_id']].append(row)
    history = RotationHistory()
    for game in sorted((g for g in games if g['date'] < cut), key=lambda g: (g['date'], g['game_id'])):
        history.observe(game, box[game['game_id']])
    season = ratings['before'][:4] + '-' + str(int(ratings['before'][:4]) + 1)[-2:]
    return {m['nba_game_id']: {s: history.change(m[s + '_nba_team_id'], m['et_date'], season, ratings, memberships) for s in ('home', 'away')}
            for m in mappings}
