"""Live 1.4 inputs: game environment and recent role for the player calibration, and the in-season team scoring shift.

Protocol: nba_live14_protocol.json. The same functions serve the validation (bet365 lines from the BetsAPI archive) and the
producer (PropLine consensus lines at sealing), so a feature means the same thing when it is fitted and when it is served.
Every input is taken from games on earlier dates only."""
from bisect import bisect_left
from collections import defaultdict
from datetime import date as Date, timedelta

import numpy as np
from scipy.stats import norm

BASE = ('logit_probability', 'bias', 'own_questionable_or_doubtful', 'own_probable', 'teammates_missing_minutes_per_48')
ENV = ('total_c', 'own_spread', 'abs_spread', 'home', 'back_to_back', 'pace_c', 'opp_def_c', 'min10', 'usage_trend')
LOOKBACK = 10        # games of a team for its pace and defence
MIN_TEAM_GAMES = 5   # fewer earlier games: the feature is 0 (league level)
LEAGUE_DAYS = 60     # window of the league means that centre the features
BETS_AS_OF = 2700    # seconds before tipoff of the bet365 line used in validation (the PropLine capture is 30-90 min before)


def possessions(rows):
    """FGA - OREB + turnovers + 0.44 FTA summed over a team's player rows; None if a row lacks a count."""
    keys = ('fga', 'oreb', 'tov', 'fta')
    if not rows or any(r.get(k) is None for r in rows for k in keys):
        return None
    total = lambda k: sum(r[k] for r in rows)
    return total('fga') - total('oreb') + total('tov') + .44 * total('fta')


def game_records(games, done=()):
    """(date, game_id, home id, away id, home points, away points, home poss, away poss) of finished games.

    `games` are rows of games.json (the extended dataset carries possessions_estimate); `done` are the producer's completed
    games of the target season, whose possessions come from their player rows."""
    out = []
    for g in games:
        h, a = g['home'], g['away']
        out.append((g['date'], g['game_id'], h['team_id'], a['team_id'], h['points'], a['points'],
                    h.get('possessions_estimate'), a.get('possessions_estimate')))
    for g in done:
        rows = g.get('players', [])
        h, a = g['home'], g['away']
        out.append((g['date'], g['game_id'], h['team_id'], a['team_id'], h['points'], a['points'],
                    possessions([r for r in rows if r['team_id'] == h['team_id']]), possessions([r for r in rows if r['team_id'] == a['team_id']])))
    return sorted(out)


class TeamHistory:
    """Per-team and league series of finished games, queried as of a cut date (strictly earlier games)."""

    def __init__(self, records):
        self.team = defaultdict(list)    # team -> [(date, poss, points allowed per possession)]
        self.league = []                 # [(date, total points, poss per team, allowed per poss)]
        for day, _, home, away, hp, ap, hposs, aposs in records:
            for team, poss, opp_points, opp_poss in ((home, hposs, ap, aposs), (away, aposs, hp, hposs)):
                allowed = opp_points / opp_poss if opp_poss else None
                self.team[team].append((day, poss, allowed))
            self.league.append((day, hp + ap, None if hposs is None or aposs is None else (hposs + aposs) / 2,
                                None if not hposs or not aposs else (hp / hposs + ap / aposs) / 2))
        self.league_days = [r[0] for r in self.league]

    def last_game(self, team, cut):
        rows = self.team.get(team, [])
        i = bisect_left([r[0] for r in rows], cut)
        return rows[i - 1][0] if i else None

    def recent(self, team, cut):
        """(mean possessions, mean points allowed per possession) of the last LOOKBACK games, or (None, None)."""
        rows = [r for r in self.team.get(team, []) if r[0] < cut][-LOOKBACK:]
        poss = [r[1] for r in rows if r[1] is not None]
        allowed = [r[2] for r in rows if r[2] is not None]
        ok = lambda v: float(np.mean(v)) if len(v) >= MIN_TEAM_GAMES else None
        return ok(poss), ok(allowed)

    def league_means(self, cut):
        """(mean game total, mean possessions per team, mean allowed per possession) over the LEAGUE_DAYS before `cut`."""
        start = (Date.fromisoformat(cut) - timedelta(days=LEAGUE_DAYS)).isoformat()
        lo, hi = bisect_left(self.league_days, start), bisect_left(self.league_days, cut)
        rows = self.league[lo:hi]
        if len(rows) < 30:  # season start: fall back to the newest 300 earlier games
            rows = self.league[max(0, hi - 300):hi]
        mean = lambda i: float(np.mean([r[i] for r in rows if r[i] is not None])) if any(r[i] is not None for r in rows) else None
        return mean(1), mean(2), mean(3)


def player_recent(hist):
    """min10 = mean minutes of the last 10 / 48; usage_trend = per-minute (FGA + 0.44 FTA + TOV) of the last 5 over the last 20, - 1."""
    min10 = float(np.mean([h['minutes'] for h in hist[-10:]])) / 48 if hist else 0.
    usage = lambda rows: (sum(h['fga'] + .44 * h['fta'] + h['tov'] for h in rows) / max(sum(h['minutes'] for h in rows), 1e-9))
    if any(h.get(k) is None for h in hist for k in ('fga', 'fta', 'tov')) or len(hist) < 10:
        return min10, 0.
    whole = usage(hist)
    return min10, (usage(hist[-5:]) / whole - 1.) if whole > 0 else 0.


def environment(team, home_team, away_team, cut, lines, history, hist):
    """The ENV vector of one player-game. `lines` = dict(spread_home, total) or None; missing inputs are 0."""
    is_home = team == home_team
    opp = away_team if is_home else home_team
    total_l, pace_l, ppp_l = history.league_means(cut)
    spread = None if not lines else lines.get('spread_home')
    total = None if not lines else lines.get('total')
    own = None if spread is None else (spread if is_home else -spread)
    last = history.last_game(team, cut)
    b2b = float(last is not None and (Date.fromisoformat(cut) - Date.fromisoformat(last)) == timedelta(days=1))
    pace_own, _ = history.recent(team, cut)
    pace_opp, allowed_opp = history.recent(opp, cut)
    min10, usage = player_recent(hist)
    return [
        0. if total is None or total_l is None else (total - total_l) / 10,
        0. if own is None else own / 10,
        0. if own is None else abs(own) / 10,
        float(is_home), b2b,
        0. if None in (pace_own, pace_opp, pace_l) else ((pace_own + pace_opp) / 2 - pace_l) / 10,
        0. if None in (allowed_opp, ppp_l) else (allowed_opp - ppp_l) * 10,
        min10, usage]


def bets_lines(rows, seconds=BETS_AS_OF):
    """game id -> dict(spread_home, total) from nba_betsapi_odds rows, the latest bet365 snapshot at least `seconds` before tipoff."""
    out = defaultdict(dict)
    for r in rows:
        if r['market'] not in ('spread_game', 'total_game'):
            continue
        entry = None
        for snap in r['path']:  # far to near
            if snap[0] >= seconds:
                entry = snap
            else:
                break
        if entry is not None:
            out[r['game_id']]['spread_home' if r['market'] == 'spread_game' else 'total'] = entry[1]
    return dict(out)


def team_shift(done, n0):
    """(home, away) points shift: mean residual of the season's finished games times n / (n + n0).

    done = [(home predicted mean, away predicted mean, home points, away points)]."""
    if not done or n0 is None:
        return 0., 0.
    n = len(done)
    home = sum(hp - hm for hm, _, hp, _ in done) / (n + n0)
    away = sum(ap - am for _, am, _, ap in done) / (n + n0)
    return float(home), float(away)


def apply_shift(prediction, shift):
    """A live_team prediction with both means moved by `shift`; probabilities recomputed at the same lines and sds."""
    if shift == (0., 0.):
        return prediction
    out = dict(prediction)
    for side, s in (('home', shift[0]), ('away', shift[1])):
        q = dict(prediction[side])
        q['mean'] = q['mean'] + s
        q['p'] = float(norm.sf(q['line'], q['mean'], q['sd']))
        out[side] = q
    t = dict(prediction['total'])
    t['mean'] = out['home']['mean'] + out['away']['mean']
    t['p'] = float(norm.sf(t['line'], t['mean'], t['sd']))
    out['total'] = t
    return out
