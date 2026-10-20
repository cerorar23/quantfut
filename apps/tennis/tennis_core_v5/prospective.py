"""Freeze a v5 protocol, seal all-market boards from verified winner parents, evaluate later results."""
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from tennis_engine.operations import now, utc
from tennis_engine.paper_validation import digest
from tennis_engine.model import ServeModel
from tennis_engine.scoring import Rules
from tennis_engine.prospective import result_valid
from tennis_engine.shadow import metadata_gate
from tennis_allmarkets_v1.contracts import contracts, forecast_board, outcome, validate_mass
from tennis_allmarkets_v1.prospective import key, metrics
from tennis_quality_v3.prospective import read, write_new, checksum
from tennis_markets_v2.catalog import MarketEngine, Contract
from tennis_core_v4 import NodeBank, MixtureEngine, weights
from scipy.optimize import brentq
from scipy.special import expit, logit
from .features import pair_features
import pandas as pd

CODE = Path(__file__).parent
KEEP = ('market_families', 'allowed_deciding_tiebreaks', 'minimum_completed_per_exact_group', 'minimum_competitions_per_group',
        'minimum_high_confidence_observations', 'maximum_absolute_calibration_gap', 'familywise_alpha', 'multiplicity_groups',
        'minimum_metric_coverage', 'grouping', 'bootstrap_blocks')


def freeze(path, params_path, old_protocol, quality_protocol, canonical, end='2027-07-01T00:00:00Z', start='2026-10-20T00:00:00Z'):
    stamp = now()
    if not utc(stamp) < utc(start):
        raise ValueError('Declare a new future interval before sealing')
    old = read(old_protocol)
    p = dict({k: old[k] for k in KEEP}, schema='tennis-core-v5-protocol-v1', created_at=stamp, evaluation_start=start, evaluation_end=end,
        params_path=str(Path(params_path).resolve()), params_sha256=digest(params_path),
        quality_protocol=str(Path(quality_protocol).resolve()), quality_protocol_sha256=digest(quality_protocol),
        code_sha256={str(f.resolve()): digest(f) for f in CODE.glob('*.py')},
        contracts={str(b): contracts(b) for b in (3, 5)}, candidate='overdispersed_mixture_elo_blend_coherent_joint',
        parent_gate='parent winner record verified at its own seal time; v5 decision strictly before the official earliest bound; no fresh 4h calendar receipt',
        supersedes='core_v4_prospective_20261019 for new events: adds rank, rank points and age to the winner blend; v4 records stay untouched',
        frozen_no_refit=True, odds_used=False, financial_validation=False, external_timestamp=False,
        development_data_note='k/sigma from 2025; stacker (Markov mixture, Elo, rank, points, age) refit on 2025+2026 frozen-origin rows after feature selection by 2025 CV; 2026 already inspected; only prospective results confirm',canonical_path=str(Path(canonical).resolve()),canonical_sha256=digest(canonical),
        quality_accredited=False)
    write_new(path, p)
    return p


def load(path):
    p = read(path)
    if p['schema'] != 'tennis-core-v5-protocol-v1' or not utc(p['created_at']) < utc(p['evaluation_start']) < utc(p['evaluation_end']):
        raise ValueError('Invalid v5 protocol')
    if digest(p['params_path']) != p['params_sha256'] or digest(p['canonical_path']) != p['canonical_sha256'] or digest(p['quality_protocol']) != p['quality_protocol_sha256']:
        raise ValueError('Frozen parameters or linked protocol changed')
    if p['contracts'] != {str(b): contracts(b) for b in (3, 5)}:
        raise ValueError('Different contract family')
    if {str(f.resolve()): digest(f) for f in CODE.glob('*.py')} != p['code_sha256']:
        raise ValueError('Frozen v5 code changed')
    return p


def parent_point(p, parent_path, decision):
    v = read(parent_path)
    sha = v.pop('payload_sha256')
    if checksum(v) != sha or v['protocol_sha256'] != p['quality_protocol_sha256']:
        raise ValueError('Invalid linked winner record')
    event, fixture, metadata = v['event'], v['fixture_receipt'], v['tournament_metadata']
    if not utc(v['sealed_at']) <= utc(decision) < utc(fixture['official_not_before']) or utc(decision) >= utc(event['commence_time']):
        raise ValueError('Decision is not before the official earliest bound')
    if not utc(p['evaluation_start']) <= utc(event['commence_time']) < utc(p['evaluation_end']):
        raise ValueError('Outside study period')
    if metadata_gate(event, metadata) or fixture.get('source_kind') != 'official_order_of_play':
        raise ValueError('Invalid original match evidence')
    for path_key, sha_key in (('calendar_source_path', 'calendar_source_sha256'), ('review_path', 'review_sha256')):
        if digest(fixture[path_key]) != fixture[sha_key]:
            raise ValueError('Archived evidence changed')
    for name, sha_value in v['artifacts'].items():
        if digest(name) != sha_value:
            raise ValueError('Frozen artifact changed')
    model_json = next(n for n in v['artifacts'] if Path(n).name == 'model.json' and Path(n).parent.name == v['circuit'] + '_current')
    point = ServeModel(Path(model_json).parent, uncertainty=False).predict(v['player_ids'][0], v['player_ids'][1], metadata['surface'], uncertainty=False)
    if point['unknown_effects']:
        raise ValueError('Missing trained player/surface effect')
    rules = Rules(metadata['best_of'], deciding_tiebreak=metadata['deciding_tiebreak'])
    if abs(MarketEngine(point['p'], point['q'], rules).probabilities(Contract('winner', 'A'))['win'] - v['variants']['model_probability']) > 1e-9:
        raise ValueError('Frozen parent Markov probability does not reproduce')
    return v, point, rules


_CANON = {}


def canonical(p):
    if p['canonical_path'] not in _CANON:
        _CANON[p['canonical_path']] = pd.read_parquet(p['canonical_path'])
    return _CANON[p['canonical_path']]


def build(p_serve, q_serve, elo, rules, params, x):
    bank = NodeBank(p_serve, q_serve, rules)
    k, s = params['k'], params['sigma']
    base = float(weights(k * bank.gap, s) @ bank.winner)
    z = (params['w_markov'] * logit(base) + params['w_elo'] * logit(elo) + params['coef_lrank'] * x['lrank']
         + params['coef_lpts'] * x['lpts'] + params['coef_age_decades'] * x['age'])
    target = float(expit(z))
    f = lambda c: float(weights(c, s) @ bank.winner) - target
    lo, hi = -1.5, 1.5
    center = brentq(f, lo, hi) if f(lo) < 0 < f(hi) else (lo if f(lo) >= 0 else hi)
    engine = MixtureEngine(bank, weights(center, s))
    engine.diagnostics = dict(markov_winner=MarketEngine(p_serve, q_serve, rules).probabilities(Contract('winner', 'A'))['win'], mixture_winner=base,
        elo_winner=float(elo), features=x, target_winner=target, final_winner=float(weights(center, s) @ bank.winner), center=float(center))
    return engine


def board(p, v, point, rules):
    params = read(p['params_path'])[v['circuit']]
    a, b = v['player_ids']
    x = pair_features(canonical(p), v['circuit'], a, b, v['event']['commence_time'])
    engine = build(point['p'], point['q'], v['variants']['surface_elo_probability'], rules, params, x)
    return forecast_board(engine), engine.diagnostics


def seal(protocol_path, parent_path, output_root):
    p = load(protocol_path)
    v, point, rules = parent_point(p, parent_path, now())
    rows, diag = board(p, v, point, rules)
    stamp = now()
    parent_point(p, parent_path, stamp)
    value = dict(schema='tennis-core-v5-sealed-v1', protocol_sha256=digest(protocol_path), parent_record_path=str(Path(parent_path).resolve()),
        parent_record_sha256=digest(parent_path), sealed_at=stamp, event=v['event'], circuit=v['circuit'], player_ids=v['player_ids'],
        competition_id=v['competition_id'], tournament_metadata=v['tournament_metadata'], serve_probabilities=point,
        winner_diagnostics=diag, rows=rows, financial_validation=False, externally_timestamped=False)
    target = Path(output_root) / (hashlib.sha256(v['event']['id'].encode()).hexdigest() + '.json')
    write_new(target, dict(value, payload_sha256=checksum(value)))
    return target


def run_seals(protocol_path, parents_root, output_root):
    load(protocol_path)
    rows = []
    for parent in sorted(Path(parents_root).glob('*.json')):
        try:
            ident = read(parent)['event']['id']
            if (Path(output_root) / (hashlib.sha256(ident.encode()).hexdigest() + '.json')).exists():
                rows.append(dict(parent=str(parent), status='already_sealed'))
                continue
            rows.append(dict(parent=str(parent), status='sealed', path=str(seal(protocol_path, parent, output_root).resolve())))
        except (ValueError, KeyError, TypeError, OSError, StopIteration) as error:
            rows.append(dict(parent=str(parent), status='excluded', reason=str(error)))
    counts = defaultdict(int)
    for r in rows:
        counts[r['status']] += 1
    return dict(evaluated_at=now(), rows=rows, statuses=dict(counts), odds_credits_used=0)


def evaluate(protocol_path, predictions_root, results_path):
    p = load(protocol_path)
    stamp = now()
    results = read(results_path)
    if not isinstance(results, list) or len({r['event_id'] for r in results}) != len(results):
        raise ValueError('Unique result events required')
    indexed = {r['event_id']: r for r in results}
    groups, rejected, rejected_results, events = defaultdict(list), [], [], 0
    for path in sorted(Path(predictions_root).glob('*.json')):
        try:
            v = read(path)
            sha = v.pop('payload_sha256')
            if checksum(v) != sha or v['protocol_sha256'] != digest(protocol_path) or digest(v['parent_record_path']) != v['parent_record_sha256']:
                raise ValueError('Changed forecast or linked parent')
            parent, point, rules = parent_point(p, Path(v['parent_record_path']), v['sealed_at'])
            expected, _ = board(p, parent, point, rules)
            if v['rows'] != expected or v['serve_probabilities'] != point:
                raise ValueError('Probabilities do not reproduce from frozen parameters')
            for row in v['rows']:
                validate_mass(row['probabilities'])
            event, meta, ident = v['event'], v['tournament_metadata'], v['event']['id']
            result = indexed.get(ident)
            if result:
                try:
                    if not result_valid(result) or utc(result['received_at']) > utc(stamp) or any(result[k] != event[k] for k in ('home_team', 'away_team', 'sport_key')):
                        raise ValueError('Result identity, physical times or original evidence invalid')
                    if result['status'] != 'walkover':
                        if not utc(v['sealed_at']) < utc(result['actual_start']):
                            raise ValueError('Prediction is not before actual start')
                        if not utc(p['evaluation_start']) <= utc(result['actual_start']) < utc(p['evaluation_end']) or result['best_of'] != meta['best_of']:
                            raise ValueError('Result outside study or rules mismatch')
                    for row in v['rows']:
                        outcome(row['contract'], result)
                except (ValueError, KeyError, TypeError) as error:
                    rejected_results.append(dict(event_id=ident, reason=str(error)))
                    result = None
            for row in v['rows']:
                g = key(dict(circuit=v['circuit'], best_of=meta['best_of'], deciding_tiebreak=meta['deciding_tiebreak'], contract=row['contract']))
                obs = outcome(row['contract'], result) if result else 'pending'
                groups[g].append(dict(event_id=ident, probabilities=row['probabilities'], outcome=obs, competition_id=v['competition_id'],
                    period=result['actual_start'][:10] if result and result.get('actual_start') else event['commence_time'][:10]))
            events += 1
        except (ValueError, KeyError, TypeError, OSError, StopIteration) as error:
            rejected.append(dict(path=str(path), reason=str(error)))
    ended, reports = utc(stamp) >= utc(p['evaluation_end']), []
    for g, rows in sorted(groups.items()):
        m = metrics(rows, p)
        gates = dict(fixed_period_complete=ended, sufficient_sample=m['sufficient_sample'], high_confidence_calibration=m['high_confidence_calibration_supported'],
                     metric_coverage=bool(m['coverage'] is not None and m['coverage'] >= p['minimum_metric_coverage']),
                     no_invalid_records=not rejected and not rejected_results)
        reports.append(dict(**json.loads(g), **m, gates=gates, eligible_for_independent_review=all(gates.values()), quality_accredited=False))
    return dict(schema='tennis-core-v5-evaluation-v1', evaluated_at=stamp, protocol_sha256=digest(protocol_path), unique_events=events,
        rejected_records=rejected, rejected_results=rejected_results, groups=reports, fixed_period_complete=ended,
        financial_validation=False, quality_accredited=False, external_preregistration_timestamp=False)
