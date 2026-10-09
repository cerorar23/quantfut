"""Exploratory regulation-minute distributions, conditional on observed exposure.

No availability model, prices, prospective receipt, or team-rotation forecast.
The caller supplies provenance-verified retrospective labels; all target-date
outcomes enter history only after that date's forecasts have been computed.
"""
from collections import defaultdict, Counter
from datetime import date
from itertools import groupby
import math
import json
from pathlib import Path

import numpy as np
from .audit import digest


def verified_namespace_overlay(rows, source_path, source_sha256):
    """Add missing namespace only through an exact archived NBA roster proof."""
    if digest(source_path) != source_sha256:
        raise ValueError('namespace source hash mismatch')
    official = json.loads(Path(source_path).read_bytes())['boxScoreTraditional']
    source = {}
    for side in ['homeTeam', 'awayTeam']:
        team = official[side]
        for person in team['players']:
            key = (official['gameId'], person['personId'])
            if key in source:
                raise ValueError('duplicate official person')
            source[key] = (team['teamId'], person)
    missing = [r for r in rows if r.get('id_namespace') is None]
    if len(missing) != len(source) or {(r['game_id'], r['player_id']) for r in missing} != set(source):
        raise ValueError('missing-namespace cohort differs from complete official roster')
    output = []
    for row in rows:
        if row.get('id_namespace') is not None:
            if row['id_namespace'] != 'nba':
                raise ValueError('conflicting existing namespace')
            output.append(row)
            continue
        tid, person = source[row['game_id'], row['player_id']]
        stats = person['statistics']
        if row['team_id'] != tid or row['status'] != person['comment'] or any(
                row[target] != stats[field] for target, field in [('points', 'points'), ('rebounds', 'reboundsTotal'), ('assists', 'assists')]):
            raise ValueError('official person/team/stat/status mismatch')
        output.append(dict(row, id_namespace='nba', namespace_proof=dict(
            source_path=str(source_path), source_sha256=source_sha256,
            source_kind='archived NBA BoxScoreTraditionalV3', game_id=row['game_id'],
            person_id=row['player_id'], team_id=tid, exact_match=True)))
    return output


def regulation_labels(box_rows, rotations):
    """Derive outcome labels from complete court intervals without rescaling."""
    grouped = defaultdict(list)
    for row in box_rows:
        if row['season_type'] == 'regular':
            grouped[row['game_id']].append(row)
    labels, seen_games = [], set()
    for game in rotations:
        gid = game['game_id']
        if gid not in grouped:
            continue
        if gid in seen_games:
            raise ValueError('duplicate rotation game')
        seen_games.add(gid)
        players = {r['player_id']: r for r in grouped[gid]}
        if len(players) != len(grouped[gid]) or any(r.get('id_namespace') != 'nba' for r in players.values()):
            raise ValueError('duplicate roster or wrong namespace')
        metadata = {(r['date'], r['season']) for r in players.values()}
        teams = {r['team_id'] for r in players.values()}
        if len(metadata) != 1 or len(teams) != 2 or game['periods'] < 4:
            raise ValueError('invalid complete-game metadata')
        intervals, minutes = defaultdict(list), defaultdict(float)
        overlay = {r['player_id'] for r in game.get('official_subsecond_participation_overlay', [])}
        for stint in game['chronological_lineups']:
            ids, tid, period = stint['nba_player_ids'], stint['team_id'], stint['period']
            a, b = stint['start_elapsed_seconds'], stint['end_elapsed_seconds']
            start = (period - 1) * 720 if period <= 4 else 2880 + (period - 5) * 300
            end = start + (720 if period <= 4 else 300)
            if tid not in teams or not 1 <= period <= game['periods'] or len(ids) != len(set(ids)) or len(ids) != 5:
                raise ValueError('invalid court identity or period')
            if not all(math.isfinite(x) for x in (a, b)) or not start <= a < b <= end:
                raise ValueError('invalid court interval')
            if any(pid not in players or players[pid]['team_id'] != tid or players[pid]['status']
                   or not (players[pid]['participated'] or pid in overlay) for pid in ids):
                raise ValueError('foreign identity or unproven participation')
            intervals[tid, period].append((a, b))
            if period <= 4:
                for pid in ids:
                    minutes[pid] += (b - a) / 60
        for tid in teams:
            for period in range(1, game['periods'] + 1):
                spans = sorted(intervals[tid, period])
                start = (period - 1) * 720 if period <= 4 else 2880 + (period - 5) * 300
                end = start + (720 if period <= 4 else 300)
                if (not spans or abs(spans[0][0] - start) > 1e-6 or abs(spans[-1][1] - end) > 1e-6
                        or any(abs(x[1] - y[0]) > 1e-6 for x, y in zip(spans, spans[1:]))):
                    raise ValueError('court coverage gap or overlap')
            if abs(sum(minutes[pid] for pid, r in players.items() if r['team_id'] == tid) - 240) > 1e-6:
                raise ValueError('regulation team minutes do not conserve240')
        for row in grouped[gid]:
            value = minutes[row['player_id']]
            if not 0 <= value <= 48 + 1e-9:
                raise ValueError('invalid individual regulation total')
            labels.append(dict(**{k: row[k] for k in ['game_id', 'player_id', 'id_namespace', 'team_id', 'season', 'season_type', 'date']},
                               regulation_minutes=min(value, 48), box_minutes=row['minutes'],
                               box_participated=row['participated'], box_status=row['status'],
                               regulation_positive=value > 0, overtime_periods=game['periods'] - 4,
                               original_historical_receipt_known=False, label_only=True))
    if seen_games != set(grouped):
        raise ValueError('regular game without complete rotation')
    return labels


def validate_rows(rows):
    seen = set()
    games = {}
    for row in rows:
        key = (row['game_id'], row['player_id'])
        if key in seen or row.get('id_namespace') != 'nba':
            raise ValueError('duplicate player/game or unverified namespace')
        seen.add(key)
        date.fromisoformat(row['date'])
        value = row['regulation_minutes']
        if not math.isfinite(value) or not 0 <= value <= 48:
            raise ValueError('regulation minutes outside [0,48]')
        if row['season_type'] != 'regular':
            raise ValueError('regular-season protocol only')
        identity = (row['date'], row['season'])
        if row['game_id'] in games and games[row['game_id']] != identity:
            raise ValueError('conflicting game metadata')
        games[row['game_id']] = identity


def forecast_minutes(history, as_of, season, protocol):
    date.fromisoformat(as_of)
    past = sorted((r for r in history if r['date'] < as_of
                   and r['season'] == season and r['season_type'] == 'regular'
                   and r['regulation_minutes'] > 0),
                  key=lambda r: (r['date'], r['game_id']))[-protocol['history_window']:]
    if len(past) < protocol['minimum_appearances']:
        return dict(status='abstain', reason='insufficient_positive_regulation_history',
                    history_count=len(past))
    values = np.asarray([r['regulation_minutes'] for r in past], dtype=float)
    baseline = values[-protocol['baseline_window']:]
    recent = values[-protocol['recent_window']:]
    weight = protocol['shrinkage_pseudo_games']
    center = float((recent.sum() + weight * values.mean()) / (len(recent) + weight))
    candidate = np.clip(values - values.mean() + center, 0, 48)
    return dict(status='retrospective_research_only', history_count=len(past),
                history_max_date=past[-1]['date'],
                history_game_ids=[r['game_id'] for r in past],
                candidate_samples=candidate.tolist(), baseline_samples=baseline.tolist(),
                candidate_mean=float(candidate.mean()), baseline_mean=float(baseline.mean()),
                conditional_on_positive_regulation_exposure=True,
                availability_known=False, original_historical_receipt_known=False,
                team_minutes_coherent=False, actionable=False)


def sample_scores(samples, outcome):
    x = np.sort(np.asarray(samples, dtype=float))
    if not len(x) or not np.isfinite(x).all() or not math.isfinite(outcome):
        raise ValueError('nonfinite or empty distribution')
    if x.min() < 0 or x.max() > 48 or not 0 <= outcome <= 48:
        raise ValueError('regulation support violated')
    n = len(x)
    crps = np.abs(x - outcome).mean() - np.dot(2 * np.arange(n) - n + 1, x) / n**2
    lo, hi = np.quantile(x, [0.1, 0.9], method='linear')
    error = float(x.mean() - outcome)
    return dict(crps=float(crps), mae=abs(error), squared_error=error**2,
                covered80=int(lo <= outcome <= hi), width80=float(hi - lo),
                lower80=float(lo), upper80=float(hi))


def summarize(rows, protocol):
    if not rows:
        return dict(rows=0, games=0, dates=0)
    result = dict(rows=len(rows), games=len({r['game_id'] for r in rows}),
                  dates=len({r['date'] for r in rows}))
    for label in ['candidate', 'baseline']:
        for metric in ['crps', 'mae', 'covered80', 'width80']:
            result[label + '_' + metric] = float(np.mean([r[label + '_' + metric] for r in rows]))
        result[label + '_rmse'] = float(np.sqrt(np.mean([r[label + '_squared_error'] for r in rows])))
    days = defaultdict(list)
    for r in rows:
        days[r['date']].append(r)
    ordered = [days[d] for d in sorted(days)]
    counts = np.asarray([len(v) for v in ordered])
    rng = np.random.default_rng(protocol['seed'])
    index = rng.integers(0, len(ordered), size=(protocol['bootstrap_replicates'], len(ordered)))
    denominator = counts[index].sum(axis=1)
    for metric in ['crps', 'mae']:
        sums = np.asarray([sum(r['candidate_' + metric] - r['baseline_' + metric] for r in v) for v in ordered])
        differences = sums[index].sum(axis=1) / denominator
        result[metric + '_difference_candidate_minus_baseline'] = float(sums.sum() / counts.sum())
        result[metric + '_difference_ci95_date_cluster'] = np.quantile(differences, [0.025, 0.975]).tolist()
    result['interval_scope'] = 'Exploratory paired date-cluster bootstrap; no multiplicity correction or prospective confirmation.'
    return result


def replay_minutes(rows, protocol):
    validate_rows(rows)
    selected = sorted(rows, key=lambda r: (r['date'], r['game_id'], r['player_id']))
    history = defaultdict(list)
    forecasts, scored, skipped = [], [], Counter()
    seasons = set(protocol['evaluation_seasons'])
    for day, group in groupby(selected, key=lambda r: r['date']):
        today = list(group)
        for row in today:
            if row['season'] not in seasons:
                continue
            if row['regulation_minutes'] <= 0:
                skipped['no_positive_regulation_exposure'] += 1
                continue
            predicted = forecast_minutes(history[row['player_id']], day, row['season'], protocol)
            if predicted['status'] == 'abstain':
                skipped[predicted['reason']] += 1
                continue
            if predicted['history_max_date'] >= day:
                raise ValueError('target-day information in forecast history')
            identity = {k: row[k] for k in ['game_id', 'player_id', 'season', 'date']}
            # Team is a post-event scoring attribute, not a forecast feature.
            forecasts.append(dict(**identity, **predicted))
            result = dict(**identity, team_id=row['team_id'], actual_regulation_minutes=row['regulation_minutes'],
                          history_count=predicted['history_count'], history_max_date=predicted['history_max_date'],
                          history_mean_band=('low_under12' if predicted['baseline_mean'] < 12 else
                                             'mid_12_to24' if predicted['baseline_mean'] < 24 else
                                             'high_24_to36' if predicted['baseline_mean'] < 36 else 'very_high_36plus'))
            for label in ['candidate', 'baseline']:
                result.update({label + '_' + k: v for k, v in sample_scores(predicted[label + '_samples'], row['regulation_minutes']).items()})
                result[label + '_mean'] = predicted[label + '_mean']
            scored.append(result)
        # No current-date label is visible to any forecast on the same date.
        for row in today:
            history[row['player_id']].append(row)
    summaries = {}
    for season in protocol['evaluation_seasons']:
        cohort = [r for r in scored if r['season'] == season]
        all_dates = sorted({r['date'] for r in selected if r['season'] == season})
        blocks = []
        for dates in np.array_split(all_dates, protocol['chronological_blocks']):
            if not len(dates):
                continue
            inside = set(dates)
            blocks.append(dict(start=str(dates[0]), end=str(dates[-1]),
                               **summarize([r for r in cohort if r['date'] in inside], protocol)))
        summaries[season] = dict(overall=summarize(cohort, protocol), blocks=blocks)
    return dict(mode='exploratory_retrospective_positive_regulation_exposure',
                protocol_version=protocol['version'], overall=summarize(scored, protocol),
                seasons=summaries, history_mean_strata={band: summarize([r for r in scored if r['history_mean_band'] == band], protocol)
                                                      for band in sorted({r['history_mean_band'] for r in scored})},
                skipped=dict(skipped), candidate_promoted=False, F4_gate_passed=False,
                limitations=['Observed positive regulation participants define the evaluation subset after the event.',
                             'No original pregame receipts or availability/roster model; retrospective chronology only.',
                             'No team-coherent forecast, fit of hierarchical role model, or overtime-duration model.',
                             'Historical seasons already inspected; no untouched confirmatory test.',
                             'Minutes only; no quotes, contracts, EV, CLV, ROI, or deployment.']), forecasts, scored
