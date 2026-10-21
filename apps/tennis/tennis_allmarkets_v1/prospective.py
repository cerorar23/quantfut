"""Frozen multi-market study, separate from the externally stamped winner study."""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib
import json
import math
from tennis_engine.operations import now, utc
from tennis_engine.paper_validation import digest
from tennis_engine.model import ServeModel
from tennis_engine.scoring import Rules
from tennis_engine.prospective import result_valid
from tennis_engine.shadow import metadata_gate, verified_fixture
from tennis_engine.benchmark import probability_metrics
from tennis_markets_v2.catalog import MarketEngine, KINDS, Contract
from tennis_quality_v3.prospective import read, write_new, checksum, load as load_quality
from tennis_quality_v3.evaluation import block_interval, normalized_name
from .contracts import contracts, forecast_board, score_labels, validate_mass, outcome


def key(contract: dict) -> str:
    return json.dumps(contract, sort_keys=True, separators=(',', ':'))


def freeze(path: Path, quality_protocol: Path) -> dict:
    q = load_quality(quality_protocol)
    stamp = now()
    if not utc(stamp) < utc(q['evaluation_start']):
        raise ValueError('Declare a new future interval before starting the study')
    import tennis_markets_v2
    code = [*Path(__file__).parent.glob('*.py'), *Path(tennis_markets_v2.__file__).parent.glob('*.py')]
    scope = {str(bo): contracts(bo) for bo in (3, 5)}
    p = dict(schema='tennis-all-markets-protocol-v1', created_at=stamp,
        evaluation_start=q['evaluation_start'], evaluation_end=q['evaluation_end'],
        quality_protocol=str(Path(quality_protocol).resolve()), quality_protocol_sha256=digest(quality_protocol),
        code_sha256={str(f.resolve()): digest(f) for f in code}, contracts=scope,
        market_families=sorted(KINDS), candidate='coherent_joint_markov_MAP',
        condition='completed_match', first_server='unknown_equal_mixture',
        allowed_deciding_tiebreaks=[7, 10], fixture_max_age_seconds=14400,
        fixture_condition='archived scheduled fixture AND decision strictly before official earliest bound',
        minimum_completed_per_exact_group=500, minimum_competitions_per_group=30,
        minimum_high_confidence_observations=200, maximum_absolute_calibration_gap=.05,
        familywise_alpha=.05, multiplicity_groups=4 * sum(len(v) for v in scope.values()),
        minimum_metric_coverage=.8, thresholds_are_design_choices=True,
        grouping=['circuit', 'best_of', 'deciding_tiebreak', 'exact_contract'],
        complements_are_not_independent=True, correct_score_is_one_multiclass_task=True,
        bootstrap_blocks=['competition_id', 'UTC_actual_start_date'],
        frozen_no_refit=True, odds_used=False, financial_validation=False,
        external_timestamp=False, previous_DigiCert_stamp_does_not_cover_this_protocol=True,
        independent_source_review_required=True, quality_accredited=False)
    write_new(path, p)
    return p


def load(path: Path) -> dict:
    p = read(path)
    if p['schema'] != 'tennis-all-markets-protocol-v1' or not utc(p['created_at']) < utc(p['evaluation_start']) < utc(p['evaluation_end']):
        raise ValueError('Invalid multi-market protocol')
    if digest(p['quality_protocol']) != p['quality_protocol_sha256']:
        raise ValueError('Linked quality protocol changed')
    load_quality(p['quality_protocol'])
    if p['contracts'] != {str(bo): contracts(bo) for bo in (3, 5)}:
        raise ValueError('Different predefined contract family')
    import tennis_markets_v2
    active = {f.name: f for f in Path(__file__).parent.glob('*.py')}
    market = {f.name: f for f in Path(tennis_markets_v2.__file__).parent.glob('*.py')}
    for name, sha in p['code_sha256'].items():
        file = Path(name)
        local = (market if file.parent.name == 'tennis_markets_v2' else active).get(file.name)
        if digest(file) != sha or local is None or digest(local) != sha:
            raise ValueError('Frozen market or study code changed')
    expected = {(Path(n).parent.name, Path(n).name) for n in p['code_sha256']}
    actual = {(f.parent.name, f.name) for f in [*active.values(), *market.values()]}
    if expected != actual:
        raise ValueError('Active module inventory changed')
    return p


def verify_parent(p: dict, parent_path: Path, decision: str) -> tuple[dict, dict]:
    """Original winner record remains unchanged; a NEW market timestamp is used."""
    v = read(parent_path)
    sha = v.pop('payload_sha256')
    q = load_quality(p['quality_protocol'])
    if checksum(v) != sha or v['protocol_sha256'] != p['quality_protocol_sha256'] or v['artifacts'] != q['artifacts']:
        raise ValueError('Invalid linked winner record')
    event, fixture, metadata = v['event'], v['fixture_receipt'], v['tournament_metadata']
    if not utc(q['created_at']) < utc(v['sealed_at']) <= utc(decision) < utc(event['commence_time']):
        raise ValueError('Winner record or new market decision is not pre-match')
    if not utc(p['evaluation_start']) <= utc(event['commence_time']) < utc(p['evaluation_end']):
        raise ValueError('Outside future market period')
    if metadata_gate(event, metadata) or not verified_fixture(event, fixture, v['sealed_at'])['eligible']:
        raise ValueError('Invalid original match evidence')
    if fixture.get('source_kind') != 'official_order_of_play' or not utc(decision) < utc(fixture['official_not_before']):
        raise ValueError('A future published earliest bound is mandatory for this adapter')
    if not verified_fixture(event, fixture, decision, p['fixture_max_age_seconds'])['eligible']:
        raise ValueError('Archived fixture outside declared four-hour evidence window')
    if not 0 <= (utc(decision)-utc(fixture['calendar_received_at'])).total_seconds() <= p['fixture_max_age_seconds']:
        raise ValueError('Calendar receipt expired')
    for path_key, sha_key in [('calendar_source_path','calendar_source_sha256'), ('review_path','review_sha256')]:
        if digest(fixture[path_key]) != fixture[sha_key]:
            raise ValueError('Archived calendar or exact-pair review changed')
    circuit = v['circuit']
    if circuit not in ('ATP', 'WTA') or not event['sport_key'].startswith('tennis_'+circuit.lower()+'_'):
        raise ValueError('Invalid circuit')
    model = ServeModel(Path(q['data_root']) / f'models/{circuit}_current', uncertainty=False)
    a, b = v['player_ids']
    excluded = read(q['identity_review_path'])['circuits'][circuit]['excluded_ids']
    if a == b or any(pid not in model.names or pid in excluded for pid in (a,b)):
        raise ValueError('Ambiguous or unknown player identity')
    if [normalized_name(model.names[pid]) for pid in (a,b)] != [normalized_name(event[k]) for k in ('home_team','away_team')]:
        raise ValueError('Oriented participants differ')
    point = model.predict(a, b, metadata['surface'], uncertainty=False)
    if point['unknown_effects']:
        raise ValueError('Missing trained player/surface effect')
    return v, point


def seal(protocol_path: Path, parent_path: Path, predictions_root: Path) -> Path:
    p = load(protocol_path)
    at = now()
    if not utc(p['created_at']) <= utc(at):
        raise ValueError('Protocol unavailable at decision')
    parent, point = verify_parent(p, parent_path, at)
    metadata = parent['tournament_metadata']
    engine = MarketEngine(point['p'], point['q'], Rules(metadata['best_of'], deciding_tiebreak=metadata['deciding_tiebreak']))
    if abs(engine.probabilities(Contract('winner','A'))['win'] - parent['variants']['model_probability']) > 1e-9:
        raise ValueError('Frozen parent Markov probability does not reproduce')
    rows = forecast_board(engine)
    stamp = now()
    verify_parent(p, parent_path, stamp)  # Second clock/evidence check after calculation.
    value = dict(schema='tennis-all-markets-sealed-v1', protocol_sha256=digest(protocol_path),
        parent_record_path=str(Path(parent_path).resolve()), parent_record_sha256=digest(parent_path),
        sealed_at=stamp, parent_winner_sealed_at=parent['sealed_at'],
        event=parent['event'], circuit=parent['circuit'], player_ids=parent['player_ids'],
        competition_id=parent['competition_id'], tournament_metadata=metadata,
        serve_probabilities=point, rows=rows, financial_validation=False, externally_timestamped=False)
    target = Path(predictions_root) / (hashlib.sha256(parent['event']['id'].encode()).hexdigest()+'.json')
    write_new(target, dict(value, payload_sha256=checksum(value)))
    return target


def run_seals(protocol_path: Path, parents_root: Path, output_root: Path) -> dict:
    load(protocol_path)
    if not Path(parents_root).is_dir():
        raise ValueError('Existing parent forecast ledger required')
    rows = []
    for parent in sorted(Path(parents_root).glob('*.json')):
        try:
            identity=read(parent)['event']['id']
            target = Path(output_root) / (hashlib.sha256(identity.encode()).hexdigest()+'.json')
            if target.exists():
                rows.append(dict(parent=str(parent), status='already_sealed')); continue
            path = seal(protocol_path, parent, output_root)
            rows.append(dict(parent=str(parent), status='sealed', path=str(path.resolve())))
        except (ValueError, KeyError, TypeError, OSError) as error:
            rows.append(dict(parent=str(parent), status='excluded', reason=str(error)))
    return dict(evaluated_at=now(), rows=rows, statuses=dict(Counter(r['status'] for r in rows)), odds_credits_used=0)


def metrics(rows: list[dict], p: dict) -> dict:
    action = [r for r in rows if r['outcome'] not in ('pending', 'outside_completed_contract')]
    binary = [r for r in action if r['outcome'] in ('win', 'loss')]
    conditional = probability_metrics([int(r['outcome']=='win') for r in binary],
        [r['probabilities']['win'] / (1-r['probabilities']['push']) for r in binary]) if binary else None
    losses = [-math.log(max(1e-12, r['probabilities'][r['outcome']])) for r in action]
    briers = [sum((prob - int(label==r['outcome']))**2 for label,prob in r['probabilities'].items()) for r in action]
    categorical = bool(action and 'win' not in action[0]['probabilities'])
    confidences = []
    for r in action:
        label = max(r['probabilities'], key=r['probabilities'].get)
        confidences.append((r, r['probabilities'][label], int(label == r['outcome'])))
    # Pushes remain in the proper vector scores; binary ECE is conditional on action.
    bands = []
    alpha = p['familywise_alpha'] / p['multiplicity_groups']
    for low, high in ((.5,.6),(.6,.7),(.7,.8),(.8,.9),(.9,1.)):
        selected = [(r,c,y) for r,c,y in confidences if low <= c and (c < high or high==1 and c<=high)]
        gaps = [y-c for r,c,y in selected]
        intervals = {block: block_interval(gaps, [r[block] for r,c,y in selected], draws=2000, alpha=alpha / 10)
                     for block in ('competition_id','period')}
        bands.append(dict(lower=low, upper=high, n=len(selected),
            mean_probability=sum(c for r,c,y in selected)/len(selected) if selected else None,
            observed_rate=sum(y for r,c,y in selected)/len(selected) if selected else None,
            corrected_calibration_gap_intervals=intervals))
    high = [b for b in bands if b['lower'] >= .7 and b['n'] >= p['minimum_high_confidence_observations']]
    calibrated = bool(high) and all(ci is not None and max(abs(v) for v in ci) <= p['maximum_absolute_calibration_gap']
        for b in high for ci in b['corrected_calibration_gap_intervals'].values())
    blocks = len({r['competition_id'] for r in action})
    return dict(registered=len(rows), evaluated=len(action), pending=sum(r['outcome']=='pending' for r in rows),
        outside_completed_contract=sum(r['outcome']=='outside_completed_contract' for r in rows),
        pushes=sum(r['outcome']=='push' for r in rows), coverage=len(action)/len(rows) if rows else None,
        competition_blocks=blocks, proper_vector_log_loss=sum(losses)/len(losses) if losses else None,
        proper_vector_brier=sum(briers)/len(briers) if briers else None,
        vector_brier_definition='sum over all outcome classes; not divided by class count',
        conditional_binary_metrics=conditional, correct_score_multiclass=categorical,
        calibration_bands=bands, sufficient_sample=len(action)>=p['minimum_completed_per_exact_group'] and blocks>=p['minimum_competitions_per_group'],
        high_confidence_calibration_supported=calibrated)


def evaluate(protocol_path: Path, predictions_root: Path, results_path: Path) -> dict:
    p = load(protocol_path); stamp = now(); results = read(results_path)
    if not Path(predictions_root).is_dir() or not isinstance(results, list) or len({r['event_id'] for r in results}) != len(results):
        raise ValueError('Existing forecast ledger and unique result events required')
    indexed = {r['event_id']: r for r in results}; seen=set(); groups=defaultdict(list); rejected=[]; rejected_results=[]; events=0
    for path in sorted(Path(predictions_root).glob('*.json')):
        try:
            v = read(path); sha=v.pop('payload_sha256')
            if checksum(v)!=sha or v['protocol_sha256']!=digest(protocol_path) or digest(v['parent_record_path'])!=v['parent_record_sha256']:
                raise ValueError('Changed forecast or linked parent')
            if not utc(p['created_at']) <= utc(v['sealed_at']) <= utc(stamp): raise ValueError('Invalid seal time')
            parent, point=verify_parent(p, Path(v['parent_record_path']), v['sealed_at'])
            for name in ('event','circuit','player_ids','competition_id','tournament_metadata'):
                if v[name] != parent[name]: raise ValueError('Parent event differs')
            if v['serve_probabilities'] != point: raise ValueError('Frozen serve parameters differ')
            event=v['event']; identity=event['id']; metadata=v['tournament_metadata']
            if identity in seen: raise ValueError('Duplicate event forecast')
            seen.add(identity)
            if [row['contract'] for row in v['rows']] != p['contracts'][str(metadata['best_of'])]: raise ValueError('Incomplete or changed contract board')
            expected_board=forecast_board(MarketEngine(point['p'],point['q'],Rules(metadata['best_of'],deciding_tiebreak=metadata['deciding_tiebreak'])))
            if v['rows']!=expected_board: raise ValueError('Probabilities do not reproduce from frozen parameters')
            for row in v['rows']:
                probabilities=row['probabilities'];validate_mass(probabilities)
                expected=set(score_labels(metadata['best_of'])) if row['contract']['kind']=='correct_score' else {'win','push','loss'}
                if set(probabilities)!=expected: raise ValueError('Wrong outcome classes')
            result=indexed.get(identity)
            if result:
                try:
                    if not result_valid(result) or utc(result['received_at'])>utc(stamp) or any(result[k]!=event[k] for k in ('home_team','away_team','sport_key')):
                        raise ValueError('Result identity, physical times or original evidence invalid')
                    if result['status']!='walkover' and not utc(v['sealed_at'])<utc(result['actual_start']): raise ValueError('Prediction is not before actual start')
                    if result['status']!='walkover' and not utc(p['evaluation_start'])<=utc(result['actual_start'])<utc(p['evaluation_end']): raise ValueError('Actual match outside study')
                    if result['status']!='walkover' and result['best_of']!=metadata['best_of']: raise ValueError('Result rules mismatch')
                    # Validate every outcome before appending any group from this event.
                    for row in v['rows']: outcome(row['contract'],result)
                except (ValueError,KeyError,TypeError) as error:
                    rejected_results.append(dict(event_id=identity,reason=str(error)))
                    result=None  # Keep the registered event in every coverage denominator.
            event_rows=[]
            for row in v['rows']:
                group=key(dict(circuit=v['circuit'], best_of=metadata['best_of'], deciding_tiebreak=metadata['deciding_tiebreak'], contract=row['contract']))
                observed=outcome(row['contract'], result) if result else 'pending'
                if observed in ('win','loss') and row['probabilities']['push'] >= 1:
                    raise ValueError('Observed action incompatible with guaranteed unplayed period')
                event_rows.append((group,dict(event_id=identity, probabilities=row['probabilities'], outcome=observed,
                    competition_id=v['competition_id'], period=result['actual_start'][:10] if result and result.get('actual_start') else event['commence_time'][:10])))
            for group,row in event_rows: groups[group].append(row)
            events+=1
        except (ValueError, KeyError, TypeError, OSError) as error:
            rejected.append(dict(path=str(path), reason=str(error)))
    reports=[]; ended=utc(stamp)>=utc(p['evaluation_end'])
    for group, rows in sorted(groups.items()):
        m=metrics(rows,p)
        gates=dict(fixed_period_complete=ended, sufficient_sample=m['sufficient_sample'],
            metric_coverage=bool(m['coverage'] is not None and m['coverage']>=p['minimum_metric_coverage']),
            high_confidence_calibration=m['high_confidence_calibration_supported'], no_invalid_records=not rejected and not rejected_results)
        reports.append(dict(**json.loads(group), **m, gates=gates, eligible_for_independent_review=all(gates.values()), quality_accredited=False))
    return dict(schema='tennis-all-markets-evaluation-v1', evaluated_at=stamp, protocol_sha256=digest(protocol_path),
        unique_events=events, rejected_records=rejected, rejected_results=rejected_results, groups=reports,
        market_families={kind:dict(registered_contract_rows=sum(g['registered'] for g in reports if g['contract']['kind']==kind),
            evaluated_contract_rows=sum(g['evaluated'] for g in reports if g['contract']['kind']==kind), quality_accredited=False) for kind in sorted(KINDS)},
        fixed_period_complete=ended, financial_validation=False, quality_accredited=False,
        external_preregistration_timestamp=False, effective_sample_unit='unique event per exact contract, not quoted offers',
        limitations=['local hashes do not independently attest existence time', 'bootstrap does not remove all repeated-player dependence',
            'raw coherent Markov marginals require prospective calibration evidence', 'unobserved contracts and rules are not validated'])
