"""Winner: margin Elo weighted by the current rotation (nba_roster_elo_protocol.json).

Each rotation player carries the current margin Elo of the teams he played his recent minutes for; the team's effective Elo
blends its own Elo with the rotation's weighted mean. A player who played all his recent minutes for the team carries exactly
its Elo, so a team without newcomers is unchanged. Every quantity for date d uses only games strictly before d."""
from collections import defaultdict, deque
from datetime import date

from . import multimarket_v12 as v12

ROTATION_GAMES, PLAYER_APPEARANCES = 5, 30
WEIGHTS = ('minutes', 'production')


def production(r):
    return sum(r.get(k) or 0 for k in ('points', 'rebounds', 'assists', 'steals', 'blocks')) - (r.get('tov') or 0)


def effective_gaps(games, players, protocol, weights, alpha):
    """game_id -> dict(gap, base_gap): the effective and the plain margin Elo gap (home - away) at the start of its date.

    The margin Elo pass is the one of v12.team_games (same season regression, K, home edge and margin multiplier)."""
    if weights not in WEIGHTS:
        raise ValueError('unknown weights ' + weights)
    days, box = defaultdict(list), defaultdict(list)
    for g in games:
        days[g['date']].append(g)
    for r in players:
        if r.get('participated') and (r.get('minutes') or 0) > 0:
            box[r['game_id']].append(r)
    mov = defaultdict(lambda: 1500.)
    appearances = defaultdict(lambda: deque(maxlen=PLAYER_APPEARANCES))  # player -> (date, team, minutes, production)
    last_team, recent = {}, defaultdict(lambda: deque(maxlen=ROTATION_GAMES))  # team -> [{player: minutes}] this season
    season, out = None, {}

    def effective(team, cut):
        games_ = recent[team]
        if not games_:
            return mov[team]
        minutes = defaultdict(float)
        for played in games_:
            for p, m in played.items():
                minutes[p] += m / len(games_)
        today, num, den = date.fromisoformat(cut), 0., 0.
        for p, m in minutes.items():
            if last_team.get(p) != team:
                continue
            seen = [a for a in appearances[p] if 0 < (today - date.fromisoformat(a[0])).days <= protocol['history_max_days']]
            played = sum(a[2] for a in seen)
            if played <= 0:
                continue
            carried = sum(a[2] * mov[a[1]] for a in seen) / played
            w = m if weights == 'minutes' else m * max(0., sum(a[3] for a in seen) / played)
            num, den = num + w * carried, den + w
        if den <= 0:
            return mov[team]
        return (1 - alpha) * mov[team] + alpha * num / den

    for cut in sorted(days):
        current = days[cut][0]['season']
        if season is not None and season != current:
            for key in mov:
                mov[key] = 1500 + (mov[key] - 1500) * (1 - protocol['elo_season_regression'])
            recent.clear()
        season = current
        for g in days[cut]:
            h, a = g['home']['team_id'], g['away']['team_id']
            out[g['game_id']] = dict(gap=effective(h, cut) - effective(a, cut), base_gap=mov[h] - mov[a])
        for g in days[cut]:
            h, a = g['home'], g['away']
            gap = mov[h['team_id']] - mov[a['team_id']] + protocol['elo_home']
            expected = 1 / (1 + 10 ** (-gap / 400))
            result = int(h['points'] > a['points'])
            factor = v12.mov_multiplier(h['points'] - a['points'], gap if result else -gap)
            delta = protocol['elo_k'] * factor * (result - expected)
            mov[h['team_id']] += delta
            mov[a['team_id']] -= delta
        for g in days[cut]:
            played = defaultdict(dict)
            for r in box[g['game_id']]:
                played[r['team_id']][r['player_id']] = r['minutes']
                appearances[r['player_id']].append((cut, r['team_id'], r['minutes'], production(r)))
                last_team[r['player_id']] = r['team_id']
            for side in ('home', 'away'):
                recent[g[side]['team_id']].append(played.get(g[side]['team_id'], {}))
    return out


def apply(rows, gaps):
    """Copies of v12.team_games rows with elo_gap_mov replaced by the effective gap (checks the plain gap matches)."""
    out = []
    for r in rows:
        g = gaps[r['game_id']]
        if abs(g['base_gap'] - r['elo_gap_mov']) > 1e-6:
            raise ValueError('margin Elo pass differs from v12.team_games at ' + r['game_id'])
        out.append(dict(r, elo_gap_mov=g['gap'], elo_gap_base=g['base_gap']))
    return out
