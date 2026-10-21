"""v1.3 winner probabilities against Pinnacle no-vig prices (needs the cached snapshots from odds_history).

Research only: it answers whether the model adds information over the market, never produces a bet."""
from collections import defaultdict
import gzip
import json
from pathlib import Path

import numpy as np

from . import availability as av
from . import multimarket as m1
from . import multimarket_v12 as v12
from . import multimarket_v13 as v13
from .audit import write_json


def model_winner(players, games, v12_protocol, injury_path, api_dir):
    """Season -> rows of (game, date, model home-win probability, outcome), same fit as v1.3 evaluate."""
    seasons = sorted({g['season'] for g in games})
    index = {(r['game_id'], str(r['player_id'])): r for r in players}
    statuses, observed = av.status_map(av.read_reports(injury_path), av.tipoff_map(api_dir, games))
    entries = av.trailing_entries(players, games, statuses, observed)
    game_season = {g['game_id']: g['season'] for g in games}
    by_season = defaultdict(list)
    for r in v12.team_games(games, v12_protocol):
        by_season[r['season']].append(r)
    out = {}
    for season in [v12_protocol['selection_season']] + v12_protocol['test_seasons']:
        start, end = v12.training_window(season, seasons, v12_protocol)
        train_seasons = [s for s in seasons if s > v12_protocol['burn_in_season'] and start <= v12.season_start(s) < end]
        table = av.play_table(statuses, index, {g for g in observed if game_season.get(g) in train_seasons})
        train = [dict(r) for s in train_seasons for r in by_season[s]]
        test = [dict(r) for r in by_season[season]]
        v13.attach(train, entries, table)
        v13.attach(test, entries, table)
        predictions, _ = v13.team_predictions(train, test)
        out[season] = [dict(game_id=r['game_id'], date=r['date'], model=p['winner'], y=r['home_win'])
                       for r, p in zip(test, predictions)]
    return out


def join(model_rows, odds_rows):
    """Games with both a model probability and a market price taken before tipoff."""
    market = {o['game_id']: o for o in odds_rows}
    return [dict(m, market=market[m['game_id']]['home_no_vig'], overround=market[m['game_id']]['overround'],
                 minutes_to_tipoff=market[m['game_id']]['minutes_to_tipoff'])
            for m in model_rows if m['game_id'] in market]


def compare_to_market(rows, protocol):
    """Model vs market vs an equal logit blend; paired Brier differences with a date-block bootstrap."""
    if not rows:
        return dict(n=0)
    dates = [r['date'] for r in rows]
    y = [r['y'] for r in rows]
    model = np.array([r['model'] for r in rows])
    market = np.array([r['market'] for r in rows])
    logit = lambda p: np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
    blend = 1 / (1 + np.exp(-(logit(model) + logit(market)) / 2))
    return dict(
        n=len(rows), mean_overround=float(np.mean([r['overround'] for r in rows])),
        mean_minutes_to_tipoff=float(np.mean([r['minutes_to_tipoff'] for r in rows])),
        model_vs_market=v12.compare(dates, y, model, market, protocol),
        blend_vs_market=v12.compare(dates, y, blend, market, protocol),
        correlation=float(np.corrcoef(model, market)[0, 1]) if len(rows) > 2 else None,
        mean_abs_gap=float(np.mean(np.abs(model - market))))


def main():
    import argparse
    from . import odds_history as oh
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True)
    parser.add_argument('--v12-protocol', required=True)
    parser.add_argument('--injuries', required=True)
    parser.add_argument('--api-dir', required=True)
    parser.add_argument('--plan-file', required=True)
    parser.add_argument('--cache', required=True)
    parser.add_argument('--output', required=True)
    a = parser.parse_args()
    games = json.loads((Path(a.data) / 'games.json').read_bytes())
    protocol = json.loads(Path(a.v12_protocol).read_bytes())
    players = m1.read_rows(Path(a.data) / 'players.jsonl.gz')
    odds, stats = oh.load(json.loads(Path(a.plan_file).read_bytes()), a.cache, games)
    per_season = model_winner(players, games, protocol, a.injuries, a.api_dir)
    report = dict(retrospective_not_confirmatory=True, odds_load=stats,
                  seasons={s: compare_to_market(join(rows, odds), protocol) for s, rows in per_season.items()})
    Path(a.output).mkdir(parents=True, exist_ok=True)
    write_json(Path(a.output) / 'market_comparison.json', report)
    print(json.dumps({s: v.get('n') for s, v in report['seasons'].items()}))


if __name__ == '__main__':
    main()
