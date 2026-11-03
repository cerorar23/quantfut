"""Rebuild the live NBA fit with every validated earlier-day current-season box and archived pregame report."""
import argparse
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
import gzip
import hashlib
import json
from pathlib import Path

from . import availability as av
from . import current_rosters as cr
from . import injury_pdf
from . import live_features as lf
from . import multimarket_v12 as v12
from . import multimarket_v13 as v13
from . import multimarket_v13_live as live
from . import training_data as td
from .audit import digest, write_json
from .context import name_key


def current_reports(cohorts, players, identities=()):
    ids, history = live.history_index(players)
    candidates = defaultdict(set)
    for row in identities:
        candidates[name_key(row['name'])].add(str(row['player_id']))
    for key, values in candidates.items():
        if len(values) == 1:
            ids.setdefault(key, next(iter(values)))
    reports, unknown = [], set()
    for path in sorted(Path(cohorts).glob('*/bundle.json')):
        bundle = json.loads(path.read_bytes())
        metadata = bundle.get('report')
        if not metadata:
            continue
        pdf = path.parent / 'reports' / metadata['pdf_file']
        if pdf.name != metadata['pdf_file'] or digest(pdf) != metadata['pdf_sha256']:
            raise ValueError('archived current report changed')
        report = injury_pdf.extract_report(pdf, metadata['source_url'], metadata['first_received_at_utc'])
        schedule = json.loads((path.parent / 'schedule.json').read_bytes())['games']
        mapped = []
        for game in schedule:
            tip = datetime.fromisoformat(game['tipoff_utc'])
            if max(cr.utc(report['report_timestamp_utc']), cr.utc(report['first_received_at_utc'])) > tip - av.LEAD:
                continue
            matchup = game['away_tricode'] + '@' + game['home_tricode']
            label = datetime.strptime(game['et_date'], '%Y-%m-%d').strftime('%m/%d/%Y')
            teams = {name_key(game[s + '_team']): game[s + '_nba_team_id'] for s in ('home', 'away')}
            for row in report['rows']:
                if row['game_date'] != label or row['matchup'] != matchup:
                    continue
                player = ids.get(live.report_name(row['player_name_raw'])) if row.get('player_name_raw') else None
                if row.get('player_name_raw') and not player:
                    unknown.add(row['player_name_raw'])
                mapped.append(dict(row, nba_game_id=game['nba_game_id'], nba_player_id=player,
                                   nba_team_id=teams.get(name_key(row['team'])), game_tipoff_utc=game['tipoff_utc']))
        if mapped:
            reports.append(dict(report, rows=mapped))
    return reports, sorted(unknown)


def merged_reports(historical, current, output):
    with gzip.open(output, 'wt', encoding='utf8') as target:
        with gzip.open(historical, 'rt', encoding='utf8') as source:
            for line in source:
                target.write(line)
        for report in current:
            target.write(json.dumps(report, sort_keys=True) + '\n')


def run(args, now=None, get=live.http_get):
    now = now or datetime.now(UTC)
    cut = now.astimezone(live.EASTERN).date().isoformat()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    data = Path(args.data)
    players, games = td.read_players(data / 'players.jsonl.gz'), json.loads((data / 'games.json').read_bytes())
    done, unfinished = live.completed(args.first_day, (date.fromisoformat(cut) - timedelta(days=1)).isoformat(), get, args.cache)
    if any(g['status'] != 1 for g in unfinished):
        raise ValueError('earlier current-season games are not final')
    players, games = td.append_completed(players, games, done, cut)
    training = out / 'data'
    training.mkdir()
    td.write_players(training / 'players.jsonl.gz', players)
    write_json(training / 'games.json', games)
    coverage = td.audit(players, games)
    coverage['current_season_games'] = sum(g['season'] == live.SEASON for g in games)
    coverage['current_season_rows'] = sum(r['season'] == live.SEASON for r in players)
    coverage['current_season_players'] = len({r['player_id'] for r in players if r['season'] == live.SEASON})
    if coverage['current_season_games'] < len(done):
        raise ValueError('a completed current-season game was lost')
    write_json(training / 'coverage.json', coverage)
    print(json.dumps(dict(stage='data_complete', **coverage)), flush=True)
    snapshot = cr.capture(cr.TEAM_SLUGS, live.SEASON, out / 'identity_rosters', get, lambda: datetime.now(UTC), args.cache)
    current, unknown = current_reports(args.cohorts, players, snapshot['players'])
    injury_path = out / 'reports.jsonl.gz'
    merged_reports(args.reports, current, injury_path)
    write_json(out / 'report_coverage.json', dict(current_reports=len(current), current_mapped_rows=sum(len(r['rows']) for r in current),
                                                unmatched_names=unknown, unmatched_not_imputed=True))
    root = Path(live.__file__).parents[2]
    protocol_path = root / 'multimarket_v13_live_protocol.json'
    protocol = json.loads(protocol_path.read_bytes())
    v12_path = root / 'multimarket_v12_protocol.json'
    v12p = json.loads(v12_path.read_bytes())
    options = dict(features=[*lf.BASE, *lf.ENV, 'postseason'], markets=list(live.PLAYER_MARKETS),
                   team_shift_n0=None, official_rosters=True, train_current_season=True, training_cutoff=cut,
                   player_min_history=1, role_projection=True, postseason_feature=True, regular_season_roles=True,
                   roster_strength=dict(ridge=25., weight=.25), online_strength_update=True, recalculate_published=True)
    write_json(out / 'options.json', options)
    sources = dict(live_module_sha256=live.module_digest(), availability_sha256=digest(av.__file__),
                   multimarket_v13_sha256=digest(v13.__file__), multimarket_v12_sha256=digest(v12.__file__),
                   protocol_sha256=digest(protocol_path), v12_protocol_sha256=digest(v12_path),
                   players_sha256=digest(training / 'players.jsonl.gz'), games_sha256=digest(training / 'games.json'),
                   injuries_sha256=digest(injury_path), bets_sha256=digest(args.bets), options_sha256=digest(out / 'options.json'),
                   training_data_sha256=digest(td.__file__),
                   api_sha256=hashlib.sha256(''.join(digest(p) for p in sorted(Path(args.api_dir).glob('games_*.json'))).encode()).hexdigest())
    with gzip.open(args.bets, 'rt', encoding='utf8') as stream:
        bets = [json.loads(line) for line in stream]
    fitted = live.fit_model(players, games, protocol, v12p, injury_path, args.api_dir, sources, options, bets)
    model = out / 'model'
    model.mkdir()
    write_json(model / 'model.json', fitted)
    report = dict(version=fitted['version'], information_cutoff_utc=now.isoformat(), training_cutoff=cut,
                  current_season_games=fitted['current_season_games'], current_season_players=fitted['current_season_players'],
                  training_games=fitted['fit']['train_games'], player_markets={m: f['observations'] for m, f in fitted['player_fit'].items()},
                  strength_active=fitted['roster_strength']['active'], model_sha256=digest(model / 'model.json'), coverage=coverage)
    write_json(out / 'training_report.json', report)
    print(json.dumps(report), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('data', 'reports', 'api-dir', 'bets', 'cohorts', 'cache', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--first-day', default='2026-10-20')
    run(parser.parse_args())


if __name__ == '__main__':
    main()
