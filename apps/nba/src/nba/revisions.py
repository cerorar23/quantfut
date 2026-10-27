"""Versioned recalculation of published NBA probabilities, with honest information times and separate scoring eligibility."""
from collections import defaultdict
from datetime import UTC, datetime, timedelta
import json
import math
from pathlib import Path
import shutil

from scipy.stats import norm

from . import availability as av
from . import current_rosters as cr
from . import injury_pdf
from . import live_features as lf
from . import multimarket_v13 as v13
from . import multimarket_v13_live as live
from . import roster_strength as rs
from . import training_data as td
from .audit import digest, write_json

FORMAT = 'nba-probability-revision-1'


def key(row):
    return str(row['event_id']), row['market'], str(row['player_id'])


def history(folder, original, now=None):
    """Every complete revision, oldest first, each verified. Invalid evidence never replaces a prior publication."""
    folder = Path(folder)
    seals = sorted(p for p in folder.glob('updates/*/revision.seal.json') if not p.parent.name.endswith('.partial'))
    return [verify(folder, seal.parent, original, now) for seal in seals]


def latest(folder, original, now=None):
    found = history(folder, original, now)
    return found[-1] if found else None


def scored(original, revisions):
    """Per forecast, the newest version computed before its tipoff: the one that accuracy statistics may count."""
    out = {key(f): f for f in original['forecasts']}
    for revision in revisions:
        out.update({key(f): f for f in revision['forecasts'] if f['performance_eligible']})
    return list(out.values())


def signature(forecasts):
    fields = ('estimate', 'line', 'range_low', 'range_high', 'probability_over')
    return sorted((key(f), tuple(round(float(f[k]), 9) for k in fields)) for f in forecasts)


def verify(folder, root, original, now=None):
    seal_path = root / 'revision.seal.json'
    seal = json.loads(seal_path.read_bytes())
    if digest(root / 'revision.json') != seal['sha256']:
        raise ValueError('NBA revision changed')
    revision = json.loads((root / 'revision.json').read_bytes())
    if revision['format'] != FORMAT or revision['original_bundle_sha256'] != digest(folder / 'bundle.json'):
        raise ValueError('NBA revision original mismatch')
    as_of = cr.utc(revision['recalculated_at_utc'])
    if as_of < cr.utc(original['created_at_utc']) or now is not None and as_of > now:
        raise ValueError('invalid NBA revision information time')
    if digest(root / 'model.json') != revision['model_sha256']:
        raise ValueError('NBA revision model changed')
    games = {str(g['event_id']): g for g in original['games']}
    teams = {g[s + '_nba_team_id'] for g in games.values() for s in ('home', 'away')}
    memberships = cr.verify(root / 'rosters', revision['roster_sha256'], as_of, revision['season'], teams)
    seen, published = set(), {key(f) for f in original['forecasts']}
    for forecast in revision['forecasts']:
        identity = key(forecast)
        if identity in seen or forecast['market'] not in live.LABELS or str(forecast['event_id']) not in games:
            raise ValueError('duplicate or foreign revised forecast')
        seen.add(identity)
        game = games[str(forecast['event_id'])]
        eligible = as_of < cr.utc(game['tipoff_utc'])
        if forecast['performance_eligible'] is not eligible:
            raise ValueError('post-tipoff recalculation cannot claim prospective eligibility')
        game_day = cr.utc(game['tipoff_utc']).astimezone(live.EASTERN).date().isoformat()
        if forecast['last_feature_date'] >= min(revision['information_day'], game_day):
            raise ValueError('revision uses same-day or future statistical outcomes')
        if not eligible and identity not in published:
            raise ValueError('a forecast cannot be added after tipoff')
        if forecast['market'] in live.PLAYER_MARKETS and memberships.get(str(forecast['player_id'])) != forecast['team_id']:
            raise ValueError('revised player disagrees with current official membership')
        if not all(math.isfinite(forecast[k]) for k in ('estimate', 'line', 'range_low', 'range_high', 'probability_over', 'probability_under')):
            raise ValueError('nonfinite revised probability')
        if not 0 <= forecast['probability_over'] <= 1 or abs(forecast['probability_over'] + forecast['probability_under'] - 1) > 1e-8:
            raise ValueError('invalid revised probability')
    return revision


def _report(folder, bundle):
    metadata = bundle.get('report')
    if metadata is None:
        return None
    path = Path(folder) / 'reports' / metadata['pdf_file']
    if path.name != metadata['pdf_file'] or digest(path) != metadata['pdf_sha256']:
        raise ValueError('original report changed before recalculation')
    report = injury_pdf.extract_report(path, metadata['source_url'], metadata['first_received_at_utc'])
    report['pdf_file'] = metadata['pdf_file']
    return report


def recalculate(folder, model_dir, players, games, v12_protocol, cache, props_root, now=None, get=live.http_get,
                clock=None, refresh_report=True, first_day='2026-10-20'):
    """Recompute an existing publication at its old lines; post-tipoff revisions are explicitly unscored."""
    now = now or datetime.now(UTC)
    clock = clock or (lambda: now)
    folder, model_dir = Path(folder), Path(model_dir)
    bundle = json.loads((folder / 'bundle.json').read_bytes())
    original_seal = json.loads((folder / 'bundle.seal.json').read_bytes())
    if digest(folder / 'bundle.json') != original_seal['sha256']:
        raise ValueError('cannot revise a changed original')
    model = json.loads((model_dir / 'model.json').read_bytes())
    if not (model.get('roster_strength') or {}).get('active') or model['inputs']['live_module_sha256'] != live.module_digest():
        raise ValueError('recalculation requires the fitted active-strength module')
    information_day = now.astimezone(live.EASTERN).date().isoformat()
    schedule = json.loads((folder / 'schedule.json').read_bytes())['games']
    mappings = [m for m in schedule if m['nba_game_id'] in {g['nba_game_id'] for g in bundle['games']}]
    # Point in time per game: outcomes strictly before the game's own date, never its result or later games.
    # A pending game is today's or a future date, so it still receives every completed game up to now.
    context = [dict(m) for m in mappings]
    parents = folder / 'updates'
    parents.mkdir(exist_ok=True)
    tag = now.astimezone(UTC).strftime('%Y%m%dT%H%M%S%fZ')
    temporary, destination = parents / (tag + '.partial'), parents / tag
    temporary.mkdir(exist_ok=False)
    teams = {m[s + '_nba_team_id'] for m in mappings for s in ('home', 'away')}
    roster = cr.capture(teams, live.SEASON, temporary / 'rosters', get, clock, cache)
    memberships = cr.membership(roster, clock(), live.SEASON, teams)
    # The calculation uses current information; the event's original date/tipoff remains in the publication metadata.
    before = max(m['et_date'] for m in context)
    past_games = [g for g in games if g['date'] < before]
    past_players = [r for r in players if r['date'] < before]
    ids, history = live.history_index(past_players)
    report = _report(folder, bundle)
    if refresh_report and any(cr.utc(m['tipoff_utc']) > now for m in mappings):
        fresh = live.capture_report(now.astimezone(live.EASTERN).date().isoformat(), now, temporary / 'reports', get, clock)
        if fresh is not None:
            report = fresh
    entries, summaries = {}, []
    for original, current in zip(mappings, context):
        # Reports refer to the real scheduled game, while player value histories use the explicit current information date.
        e, summary = live.game_report_entries(report, original, ids, history, lead=timedelta(0), minimum=1)
        if e is not None:
            e = {tid: [item for item in items if memberships.get(str(item[0])) == tid] for tid, items in e.items()}
        entries[original['nba_game_id']] = e
        summaries.append(summary)
    rows = live.feature_rows(past_games, [], context, v12_protocol)
    v13.attach(rows, entries, model['play_probability'])
    ratings = model['roster_strength']['ratings']
    if ratings['before'] > before:
        # The fitted ratings include games after this one: refit them from earlier games only.
        model = dict(model, roster_strength=dict(model['roster_strength'],
                                                 ratings=rs.fit_ratings(past_games, past_players, before, ratings['ridge'])))
    predictions, strength = live.strength_predictions(model, context, rows, past_games, past_players, memberships,
                                                       information_day=before)
    old_lines, originals = defaultdict(dict), {key(f): f for f in bundle['forecasts']}
    for forecast in bundle['forecasts']:
        if forecast['market'] in live.PLAYER_MARKETS:
            old_lines[forecast['nba_game_id']][forecast['market'], int(forecast['player_id'])] = dict(
                line=forecast['line'], books=forecast.get('books', 0), book_lines=forecast.get('book_lines', {}))
    glines, _ = live.prop_lines.game_lines(props_root, now, mappings)
    # Same rule as the seal: without a line archive there are no player markets to revise.
    player_rows, player_summary = live.player_forecasts(model, v12_protocol, context, old_lines,
        live.player_history(past_players), entries, lf.TeamHistory(lf.game_records(past_games)), glines,
        roster_since=first_day, memberships=memberships) if props_root is not None else ([], {})
    last_dates = {m['nba_game_id']: max(g['date'] for g in past_games if m['home_nba_team_id'] in (
        g['home']['team_id'], g['away']['team_id']) or m['away_nba_team_id'] in (g['home']['team_id'], g['away']['team_id'])) for m in mappings}
    as_of = clock()
    revised_games, forecasts = live.cohort_forecasts(model, context, rows, summaries, entries, last_dates, as_of,
                                                    predictions=predictions, allow_after_tipoff=True)
    forecasts += player_rows
    prediction_by_game = {m['nba_game_id']: p for m, p in zip(mappings, predictions)}
    mapping_by_id = {m['nba_game_id']: m for m in mappings}
    for forecast in forecasts:
        old = originals.get(key(forecast))
        if old is not None:
            forecast['original_probability_over'] = old['probability_over']
            forecast['original_estimate'] = old['estimate']
            forecast['original_sealed_at_utc'] = old['sealed_at_utc']
            if forecast['market'] in ('team_points', 'game_total'):
                p = prediction_by_game[forecast['nba_game_id']]
                m = mapping_by_id[forecast['nba_game_id']]
                side = 'total' if forecast['market'] == 'game_total' else 'home' if forecast['team_id'] == m['home_nba_team_id'] else 'away'
                forecast['line'] = old['line']
                forecast['probability_over'] = float(norm.sf(old['line'], p[side]['mean'], p[side]['sd']))
                forecast['probability_under'] = 1 - forecast['probability_over']
            if forecast['market'] in live.PLAYER_MARKETS:
                forecast['reference'] = old['reference']
                forecast['line_source'] = old.get('line_source', 'original_publication')
        forecast['recalculated_at_utc'] = live.stamp(as_of)
        forecast['sealed_at_utc'] = live.stamp(as_of)
        forecast['performance_eligible'] = as_of < cr.utc(mapping_by_id[forecast['nba_game_id']]['tipoff_utc'])
        forecast['calculation_kind'] = 'updated_before_tipoff' if forecast['performance_eligible'] else 'recalculated_after_tipoff'
        forecast['information_before'] = mapping_by_id[forecast['nba_game_id']]['et_date']
    # A game that already started keeps exactly what was published: its forecasts are revised, never added afterwards.
    forecasts = [f for f in forecasts if f['performance_eligible'] or key(f) in originals]
    cr.membership(roster, as_of, live.SEASON, teams)
    previous = latest(folder, bundle, as_of)
    if signature(forecasts) == signature(previous['forecasts'] if previous else bundle['forecasts']):
        # Nothing published would change: keep the storage of each cohort proportional to real updates.
        shutil.rmtree(temporary)
        return dict(cohort=folder.name, revision=None, unchanged=True)
    shutil.copyfile(model_dir / 'model.json', temporary / 'model.json')
    revision = dict(format=FORMAT, version=live.VERSION, recalculated_at_utc=live.stamp(as_of), information_day=information_day,
                    original_bundle_sha256=original_seal['sha256'], model_sha256=digest(temporary / 'model.json'),
                    model_training_cutoff=model['training_cutoff'], season=live.SEASON,
                    training_seasons=model['train_seasons'], current_season_games=model['current_season_games'],
                    roster_sha256=digest(temporary / 'rosters/snapshot.json'), forecasts=forecasts,
                    withdrawn=[dict(event_id=f['event_id'], player_id=f['player_id'], market=f['market'],
                                    reason='not_eligible_under_current_verified_inputs') for k, f in originals.items()
                               if k not in {key(n) for n in forecasts}],
                    added=[dict(event_id=f['event_id'], player_id=f['player_id'], market=f['market'])
                           for f in forecasts if key(f) not in originals],
                    availability={g['nba_game_id']: dict(g['availability'], lead_minutes=0) for g in revised_games},
                    roster_strength=strength, player_summary=player_summary,
                    source_code_sha256=live.module_digest(), post_tipoff_never_scored=True)
    write_json(temporary / 'revision.json', revision)
    write_json(temporary / 'revision.seal.json', dict(sha256=digest(temporary / 'revision.json'), recalculated_at_utc=live.stamp(as_of)))
    temporary.rename(destination)
    verified = latest(folder, bundle, as_of)
    return dict(cohort=folder.name, revision=destination.name, forecasts=len(verified['forecasts']),
                withdrawn=len(verified['withdrawn']), added=len(verified['added']), changed=sum(f.get('original_probability_over') is not None and
                abs(f['probability_over'] - f['original_probability_over']) > 1e-10 for f in verified['forecasts']))


def refresh(cohorts, model_dir, data, cache, props_root=None, now=None, get=live.http_get, clock=None, all_publications=False,
            first_day='2026-10-20'):
    now = now or datetime.now(UTC)
    data, cohorts = Path(data), Path(cohorts)
    model = json.loads((Path(model_dir) / 'model.json').read_bytes())
    if not model.get('options', {}).get('recalculate_published'):
        return []
    selected = []
    for folder in sorted(p.parent for p in cohorts.glob('*/bundle.seal.json')):
        bundle = json.loads((folder / 'bundle.json').read_bytes())
        if all_publications or any(cr.utc(g['tipoff_utc']) > now for g in bundle['games']):
            previous = latest(folder, bundle, now)
            newest = cr.utc(previous['recalculated_at_utc'] if previous else bundle['created_at_utc'])
            if not all_publications and now - newest < timedelta(minutes=9):
                continue
            selected.append(folder)
    if not selected:
        return []
    players, games = td.read_players(data / 'players.jsonl.gz'), json.loads((data / 'games.json').read_bytes())
    cut = now.astimezone(live.EASTERN).date().isoformat()
    done, unfinished = live.completed(first_day, (datetime.fromisoformat(cut).date() - timedelta(days=1)).isoformat(), get, cache)
    if any(g['status'] != 1 for g in unfinished):
        raise ValueError('cannot refresh from unfinished earlier games')
    players, games = td.append_completed(players, games, done, cut)
    root = Path(live.__file__).parents[2]
    v12p = json.loads((root / 'multimarket_v12_protocol.json').read_bytes())
    output = []
    for folder in selected:
        try:
            output.append(recalculate(folder, model_dir, players, games, v12p, cache, props_root, now=now,
                                      get=get, clock=clock, refresh_report=not all_publications, first_day=first_day))
        except ValueError as error:  # one cohort's failed evidence never stops the others; the run reports it
            output.append(dict(cohort=folder.name, error=str(error)))
    return output


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('cohorts', 'model', 'data', 'cache'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--propline', type=Path)
    parser.add_argument('--all-publications', action='store_true')
    parser.add_argument('--first-day', default='2026-10-20')
    args = parser.parse_args()
    clock = lambda: datetime.now(UTC)
    print(json.dumps(refresh(args.cohorts, args.model, args.data, args.cache, args.propline, now=clock(), clock=clock,
                             all_publications=args.all_publications, first_day=args.first_day)), flush=True)


if __name__ == '__main__':
    main()
