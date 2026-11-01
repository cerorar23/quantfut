"""Public, read-only projection of sealed live v1.3 cohorts and their official results."""
from datetime import UTC, datetime
import json
import math
import os
from pathlib import Path
import threading
import time

import numpy as np

from .audit import digest
from . import current_rosters as cr
from .box_players import unique_players, participated
from . import revisions
from .dashboard import Dashboard, Server, handler
from .multimarket_dashboard import MultiDashboard
from .multimarket_v13_live import COMBOS, PLAYER_MARKETS, box_minutes, final_game

MARKETS = ('winner', 'team_points', 'game_total', *PLAYER_MARKETS)
PUBLIC = ('event_id', 'nba_game_id', 'player_id', 'player', 'market', 'market_label', 'estimate', 'range_low', 'range_high', 'line',
          'probability_over', 'probability_under', 'sealed_at_utc', 'last_feature_date', 'reference', 'conditional_participation')
PLAYER_PUBLIC = ('report_status', 'probability_play', 'books')


def utc(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def official_scores(folder, game, now):
    """Final team scores from the stored official receipt, or None while the result is absent. Raises if tampered."""
    receipt_path = Path(folder) / 'results' / game['nba_game_id'] / 'receipt.json'
    if not receipt_path.exists():
        return None
    receipt = json.loads(receipt_path.read_bytes())
    raw = receipt_path.parent / receipt['raw_file']
    if receipt['http_status'] != 200 or digest(raw) != receipt['raw_sha256'] or receipt['game_id'] != game['nba_game_id']:
        raise ValueError('official receipt changed')
    if not utc(game['tipoff_utc']) < utc(receipt['first_received_at_utc']) <= now:
        raise ValueError('official receipt time invalid')
    official = final_game(raw.read_bytes(), receipt)
    # nba.com can move a tipoff after the seal (0022600009, 23-oct: 01:30 -> 02:30 UTC). Later still means the forecast came
    # first; earlier could put the real tipoff before the seal, so that result is held.
    if (official['gameId'] != game['nba_game_id'] or official['gameStatus'] != 3
            or utc(official['gameTimeUTC']) < utc(game['tipoff_utc'])
            or official['homeTeam']['teamId'] != game['home_nba_team_id'] or official['awayTeam']['teamId'] != game['away_nba_team_id']):
        raise ValueError('official result identity mismatch')
    scores = {}
    for side in ('homeTeam', 'awayTeam'):
        value = official[side]['statistics']['points']
        if type(value) is not int or value < 0 or value != official[side]['score']:
            raise ValueError('final team scores do not reconcile')
        scores[side] = value
    if scores['homeTeam'] == scores['awayTeam']:
        raise ValueError('final team scores do not reconcile')
    players = {}
    for side in ('homeTeam', 'awayTeam'):
        for person in unique_players(official[side]['players']):
            stats = person['statistics']
            row = dict(minutes=box_minutes(stats['minutes']), points=stats['points'], rebounds=stats['reboundsTotal'],
                       participated=participated(stats),
                       assists=stats['assists'], threes=stats.get('threePointersMade'), steals=stats.get('steals'),
                       blocks=stats.get('blocks'), turnovers=stats.get('turnovers'))
            for market, parts in COMBOS.items():
                values = [row[p] for p in parts]
                row[market.removeprefix('player_')] = None if None in values else sum(values)
            players[person['personId']] = row
    return dict(home=scores['homeTeam'], away=scores['awayTeam'], players=players, received_at_utc=receipt['first_received_at_utc'])


def outcome(forecast, game, scores):
    if scores is None:
        return dict(status='pending', actual=None)
    market = forecast['market']
    if market in PLAYER_MARKETS:
        # conditional on playing, as books void a player who does not take the floor
        player = scores['players'].get(forecast['player_id'])
        if player is None or not player.get('participated', player['minutes'] > 0):
            return dict(status='dnp', actual=None)
        actual = player.get(market.removeprefix('player_'))
        if actual is None:
            return dict(status='result_unavailable', actual=None)
        return dict(status='evaluated', actual=actual)
    if market == 'winner':
        actual = int(scores['home'] > scores['away'])
    elif market == 'team_points':
        actual = scores['home'] if forecast['team_id'] == game['home_nba_team_id'] else scores['away']
    else:
        actual = scores['home'] + scores['away']
    return dict(status='evaluated', actual=actual)


def scorecard(rows):
    out = {}
    for market in MARKETS:
        done = [r for r in rows if r['market'] == market and r['result']['status'] == 'evaluated'
                and r.get('performance_eligible', True)]
        if not done:
            out[market] = dict(n=0)
            continue
        y = np.array([r['result']['actual'] if market == 'winner' else int(r['result']['actual'] > r['line']) for r in done], float)
        p = np.clip(np.array([r['probability_over'] for r in done]), 1e-9, 1 - 1e-9)
        out[market] = dict(n=len(done), brier=float(np.mean((p - y) ** 2)),
                           logloss=float(np.mean(-y * np.log(p) - (1 - y) * np.log1p(-p))), hit_rate=float(np.mean((p >= .5) == (y == 1))))
    return out


class LiveCohort:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.bundle = self.load()

    def load(self):
        seal = json.loads((self.folder / 'bundle.seal.json').read_bytes())
        if digest(self.folder / 'bundle.json') != seal['sha256']:
            raise ValueError('live cohort bundle changed')
        bundle = json.loads((self.folder / 'bundle.json').read_bytes())
        for name, field in (('model.json', 'model_sha256'), ('schedule.json', 'schedule_sha256'), ('completed_games.json', 'completed_sha256')):
            if digest(self.folder / name) != bundle[field]:
                raise ValueError(f'live cohort {name} changed')
        if bundle['actionable'] is not False or not bundle['version'].startswith('nba-multimarket-live-'):
            raise ValueError('unexpected live cohort')
        games = {g['event_id']: g for g in bundle['games']}
        memberships = None
        if bundle.get('roster') is not None:
            roster = bundle['roster']
            teams = {g[side + '_nba_team_id'] for g in games.values() for side in ('home', 'away')}
            memberships = cr.verify(self.folder / 'rosters', roster['snapshot_sha256'], utc(bundle['created_at_utc']),
                                    roster['season'], teams)
        seen = set()
        for f in bundle['forecasts']:
            game = games[f['event_id']]
            key = (f['event_id'], f['player_id'], f['market'])
            if key in seen or f['market'] not in MARKETS or f['nba_game_id'] != game['nba_game_id'] or f['actionable'] is not False:
                raise ValueError('duplicate or foreign live forecast')
            seen.add(key)
            if memberships is not None and f['market'] in PLAYER_MARKETS and (
                    memberships.get(str(f['player_id'])) != f['team_id']
                    or f['team_id'] not in (game['home_nba_team_id'], game['away_nba_team_id'])):
                raise ValueError('forecast player disagrees with official current roster')
            if utc(f['sealed_at_utc']) >= utc(game['tipoff_utc']) or f['last_feature_date'] >= f['sealed_at_utc'][:10]:
                raise ValueError('live forecast after tipoff/feature date')
            if not all(math.isfinite(f[k]) for k in ('estimate', 'line', 'probability_over', 'probability_under')) or not (
                    0 <= f['probability_over'] <= 1 and abs(f['probability_over'] + f['probability_under'] - 1) < 1e-8):
                raise ValueError('invalid live probability')
        return bundle

    def data(self, now):
        bundle = self.load()
        found = revisions.history(self.folder, bundle, now)
        revision = found[-1] if found else None
        forecasts = revision['forecasts'] if revision else bundle['forecasts']
        counted = revisions.scored(bundle, found)
        events, rows, scoring = [], [], []
        for g in bundle['games']:
            try:
                scores, held = official_scores(self.folder, g, now), False
            except (ValueError, KeyError, TypeError):
                scores, held = None, True
            tip = utc(g['tipoff_utc'])
            events.append(dict(event_id=g['event_id'], home_team=g['home_team'], away_team=g['away_team'], tipoff_utc=g['tipoff_utc'],
                               official_url=g['official_url'], availability=revision['availability'].get(g['nba_game_id'], g['availability']) if revision else g['availability'],
                               status='validation_hold' if held else 'evaluated' if scores else 'pending' if now < tip else 'awaiting_result',
                               final=scores and dict(home=scores['home'], away=scores['away'])))
            for f in forecasts:
                if f['event_id'] != g['event_id']:
                    continue
                row = {k: f[k] for k in PUBLIC}
                row.update({k: f[k] for k in PLAYER_PUBLIC if k in f})
                for field in ('recalculated_at_utc', 'original_probability_over', 'original_estimate', 'original_sealed_at_utc',
                              'performance_eligible', 'calculation_kind', 'membership_source', 'projected_minutes'):
                    if field in f:
                        row[field] = f[field]
                row['result'] = dict(status='validation_hold', actual=None) if held else outcome(f, g, scores)
                row['actionable'] = False
                rows.append(row)
            for f in counted:
                if f['event_id'] == g['event_id']:
                    scoring.append(dict(market=f['market'], line=f['line'], probability_over=f['probability_over'],
                                        result=dict(status='validation_hold', actual=None) if held else outcome(f, g, scores)))
        return dict(version=revision['version'] if revision else bundle['version'], cohort=self.folder.name, cohort_date=bundle['cohort_date'], created_at_utc=bundle['created_at_utc'],
                    train_seasons=revision['training_seasons'] if revision else bundle['train_seasons'], report=bundle['report'], events=events, predictions=rows,
                    recalculated_at_utc=revision['recalculated_at_utc'] if revision else None,
                    model_training_cutoff=revision['model_training_cutoff'] if revision else None,
                    current_season_games=revision['current_season_games'] if revision else None,
                    active_strength=bool(revision['roster_strength']['active']) if revision else bool(bundle.get('roster_strength')),
                    withdrawn=len(revision['withdrawn']) if revision else 0,
                    added=len(revision.get('added', [])) if revision else 0,
                    scorecard=scorecard(scoring), actionable=False, original_pilot_unchanged=True)


class CombinedDashboard:
    """RUN071 view unchanged, plus every live v1.3 cohort found under `live_root`. A bad cohort never hides RUN071."""

    def __init__(self, multi, live_root=None):
        self.multi, self.live_root = multi, Path(live_root) if live_root else None
        self.lock, self.cached, self.cached_at = threading.Lock(), None, 0

    def live(self, now):
        if self.live_root is None or not self.live_root.is_dir():
            return dict(state='unavailable', cohorts=[], problems=0)
        cohorts, problems = [], 0
        for folder in sorted(p for p in self.live_root.iterdir() if (p / 'bundle.seal.json').exists()):
            try:
                cohorts.append(LiveCohort(folder).data(now))
            except Exception:
                problems += 1
        return dict(state='ok' if not problems else 'validation_hold', cohorts=cohorts, problems=problems)

    def data(self):
        with self.lock:
            if self.cached is None or time.monotonic() - self.cached_at >= 15:
                self.cached = dict(self.multi.data(), live_v13=self.live(datetime.now(UTC)))
                self.cached_at = time.monotonic()
            return self.cached


def main():
    original = Dashboard('apps/nba/.local/normalized/nba_f6_run66_20261008/lifecycle', '/paper-data', '/capture-data', '/operations-data')
    live_root = os.environ.get('NBA_LIVE_COHORTS', '/live-cohorts')
    Server(('0.0.0.0', 8080), handler(CombinedDashboard(MultiDashboard(original, '/app/public-bundle'), live_root), '/app/web')).serve_forever()


if __name__ == '__main__':
    main()
