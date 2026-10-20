"""Frozen future predictive protocol and immutable winner probabilities.

No odds are required. No results enter prediction. Later result review remains
separate; passing statistical gates permits independent review, not certainty.
"""
import hashlib
import json
from pathlib import Path
import pandas as pd
from collections import Counter
from tennis_engine.benchmark import probability_metrics
from tennis_engine.operations import now, utc
from tennis_engine.paper_validation import digest
from tennis_engine.prospective import result_valid
from tennis_engine.shadow import verified_fixture, metadata_gate
from tennis_engine.research import hybrid_forecast
from tennis_engine.weighted_elo import WeightedEloModel
from .evaluation import MODELS, normalized_name, compare


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf8') as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, allow_nan=False)


def checksum(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def freeze(path, config, *, created_at=None):
    stamp = created_at or now()
    if not utc(stamp) < utc(config['evaluation_start']) < utc(config['evaluation_end']):
        raise ValueError('Genuinely future quality period required')
    value = dict(config, schema='tennis-predictive-quality-protocol-v3', created_at=stamp,
        code_sha256={str(p.resolve()): digest(p) for p in Path(__file__).parent.glob('*.py')},
        models=list(MODELS), primary_references=['weighted_elo', 'calibrated_surface_elo'],
        minimum_completed_per_circuit=500, minimum_competitions_per_circuit=30,
        primary_family_alpha=.05, primary_tests=4,
        minimum_band_observations=200, maximum_band_absolute_calibration_gap=.05,
        confidence_bands_for_review=[.7,.8,.9],
        minimum_coverage_at_probability_70=.2,
        thresholds_are_predeclared_design_choices_not_universal_certification=True,
        no_retraining_or_model_selection_on_evaluation=True,
        feature_candidates_used=[], paper_financial_validation=False,
        predictive_quality_accredited=False, individual_certainty=False)
    if not value['artifacts']:
        raise ValueError('Pinned model and identity artifacts required')
    for name, sha in value['artifacts'].items():
        if digest(name) != sha:
            raise ValueError('Artifact hash mismatch')
    write_new(path, value)
    return value


def load(path):
    value = read(path)
    if value.get('schema') != 'tennis-predictive-quality-protocol-v3' or not utc(value['created_at']) < utc(value['evaluation_start']) < utc(value['evaluation_end']):
        raise ValueError('Invalid frozen quality protocol')
    if value['models'] != list(MODELS):
        raise ValueError('Different comparison family')
    for files in (value['artifacts'], value['code_sha256']):
        if any(digest(name) != sha for name, sha in files.items()):
            raise ValueError('Frozen quality artifact or code changed')
    if {Path(name).name for name in value['code_sha256']} != {p.name for p in Path(__file__).parent.glob('*.py')} or any(
        digest(Path(__file__).parent/Path(name).name)!=sha for name,sha in value['code_sha256'].items()):
        raise ValueError('Active quality code differs from frozen candidate')
    import tennis_engine.paper_validation as active_core
    for name,sha in value['artifacts'].items():
        if Path(name).parent.name=='tennis_engine' and digest(Path(active_core.__file__).parent/Path(name).name)!=sha:
            raise ValueError('Active core code differs from frozen quality candidate')
    return value


def seal_prediction(protocol_path, event_input, output_root):
    """Caller supplies exact reviewed fixture evidence, never a result label."""
    p = load(protocol_path)
    if any(k in event_input for k in ('y','result','winner','outcome')):
        raise ValueError('Result labels cannot enter a prospective prediction')
    event = event_input['event']; circuit = event_input['circuit']
    if circuit not in ('ATP','WTA') or not event['sport_key'].startswith('tennis_'+circuit.lower()+'_'):
        raise ValueError('Circuit/event mismatch')
    if not utc(p['evaluation_start']) <= utc(event['commence_time']) < utc(p['evaluation_end']):
        raise ValueError('Event outside frozen quality period')
    model_folder = Path(p['data_root'])/'models'/f'{circuit}_current'
    names = read(model_folder/'model.json')['names']
    a,b = event_input['player_ids']
    denied = set(read(p['identity_review_path'])['circuits'][circuit]['excluded_ids'])
    if a == b or a in denied or b in denied or a not in names or b not in names:
        raise ValueError('Unknown or ambiguous canonical identity')
    if [normalized_name(names[pid]) for pid in (a,b)] != [normalized_name(event[k]) for k in ('home_team','away_team')]:
        raise ValueError('Exact oriented participant names required')
    metadata, fixture = event_input['tournament_metadata'], event_input['fixture_receipt']
    if metadata_gate(event,metadata) or not verified_fixture(event,fixture,now())['eligible']:
        raise ValueError('Fresh exact official fixture and rules required')
    prediction = hybrid_forecast(Path(p['data_root']), model_folder,
        Path(p['improvements_root'])/f'{circuit}_pool/pool.json', a,b,metadata['surface'],
        best_of=metadata['best_of'], deciding_tiebreak=metadata['deciding_tiebreak'])
    if prediction['serve']['unknown_effects']:
        raise ValueError('Untrained player/surface parameters')
    variants = dict(current_hybrid=prediction['winner_A'], model_probability=prediction['markov_A'],
        surface_elo_probability=prediction['surface_elo_A'], calibrated_surface_elo=prediction['calibrated_surface_elo_A'])
    for variant in ('weighted_elo','adaptive_elo'):
        path = Path(p['reference_paths'][circuit][variant])
        ref = WeightedEloModel.load_frozen(path,p['artifacts'][str(path)])
        if a not in ref.ratings or b not in ref.ratings:
            raise ValueError('Reference cold-start requires explicit abstention')
        variants[variant] = ref.predict(a,b)
    stamp = now()
    if not utc(p['created_at']) < utc(stamp) < utc(event['commence_time']) or not verified_fixture(event,fixture,stamp)['eligible']:
        raise ValueError('Evidence expired during calculation')
    value = dict(schema='tennis-quality-sealed-prediction-v3', protocol_sha256=digest(protocol_path),
        event=event,circuit=circuit,player_ids=[a,b], variants=variants,
        sealed_at=stamp,fixture_receipt=fixture,tournament_metadata=metadata,
        competition_id=event['sport_key']+':'+str(utc(event['commence_time']).year),
        artifacts=p['artifacts'], odds_used=False, individual_certainty=False)
    target = Path(output_root)/(hashlib.sha256(event['id'].encode()).hexdigest()+'.json')
    write_new(target,dict(value,payload_sha256=checksum(value)))
    return target


def evaluate_future(protocol_path, predictions_root, results_path, *, evaluated_at=None):
    p = load(protocol_path); stamp = evaluated_at or now(); results = read(results_path)
    if not Path(predictions_root).is_dir() or not isinstance(results,list) or len({r['event_id'] for r in results}) != len(results):
        raise ValueError('Existing forecast ledger and unique results required')
    indexed = {r['event_id']:r for r in results}; seen=set(); rows=[]; rejected=[]; pending=[]; universes=Counter()
    for path in sorted(Path(predictions_root).glob('*.json')):
        try:
            v=read(path); sha=v.pop('payload_sha256')
            if checksum(v)!=sha or v['protocol_sha256']!=digest(protocol_path) or v['artifacts']!=p['artifacts']:
                raise ValueError('Prediction changed or wrong version')
            event=v['event']; identity=event['id']
            if identity in seen:raise ValueError('Repeated forecast event')
            seen.add(identity)
            if not utc(p['created_at'])<utc(v['sealed_at'])<=utc(stamp):raise ValueError('Invalid sealing time')
            if set(v['variants']) != set(MODELS):raise ValueError('Different forecast variants')
            for probability in v['variants'].values():probability_metrics([0],[probability])
            if v['circuit'] not in ('ATP','WTA'):raise ValueError('Invalid circuit')
            if metadata_gate(event,v['tournament_metadata']) or not verified_fixture(event,v['fixture_receipt'],v['sealed_at'])['eligible']:
                raise ValueError('Invalid original fixture evidence')
            universes[v['circuit']]+=1
            r=indexed.get(identity)
            if not r:pending.append(identity);continue
            if not result_valid(r) or utc(r['received_at'])>utc(stamp):raise ValueError('Result evidence unavailable or invalid')
            if any(event.get(k)!=r.get(k) for k in ('home_team','away_team','sport_key')):raise ValueError('Result identity mismatch')
            if r['status']!='completed':pending.append(identity+':outside_completed_probability_contract');continue
            if not utc(v['sealed_at'])<utc(r['actual_start']) or not utc(p['evaluation_start'])<=utc(r['actual_start'])<utc(p['evaluation_end']):raise ValueError('Not prospective')
            rows.append(dict(match_id=identity,circuit=v['circuit'],y=int(r['official_winner']==event['home_team']),
                competition_id=v['competition_id'],period=r['actual_start'][:10],**v['variants']))
        except (ValueError,KeyError,TypeError,OSError):rejected.append(str(path))
    reports={}
    complete=utc(stamp)>=utc(p['evaluation_end'])
    for circuit in ('ATP','WTA'):
        subset=[r for r in rows if r['circuit']==circuit]
        frame=pd.DataFrame(subset,columns=['match_id','y','period','competition_id',*MODELS])
        report=compare(frame,universes[circuit],scope='frozen_future_predictive_quality')
        report['historical_availability_verified']=True
        report['limits']=['Local seals do not establish independent timestamp attestation for every order.',
                          'Result fields still require source interpretation review; hashes alone do not prove them.',
                          'Cross-tournament player dependence remains a limitation of block intervals.']
        report['competition_blocks']=frame.competition_id.nunique()
        bands=[b for b in report['models']['current_hybrid']['bands'] if b['lower']>=.7]
        supported=[b for b in bands if b['n']>=p['minimum_band_observations']]
        calibrated=bool(supported) and all(b['block_calibration_gap_ci95'] is not None and
            b['block_calibration_gap_ci95'][0]>=-p['maximum_band_absolute_calibration_gap'] and
            b['block_calibration_gap_ci95'][1]<=p['maximum_band_absolute_calibration_gap'] for b in supported)
        better=all(c[k] is not None and c[k][1]<0 for c in report['paired_comparisons'].values()
            for k in ('tournament_block_ci98_75','source_period_block_ci98_75'))
        selected=report['models']['current_hybrid']['fixed_threshold_coverage'][1]['coverage']
        report['predeclared_statistical_gate_passed']=bool(complete and not rejected and len(frame)>=p['minimum_completed_per_circuit'] and
            report['competition_blocks']>=p['minimum_competitions_per_circuit'] and calibrated and better and
            selected is not None and selected>=p['minimum_coverage_at_probability_70'])
        report['supported_probability_band_lowers']=[b['lower'] for b in supported]
        report['predictive_quality_accredited']=False  # independent source/protocol review still required
        reports[circuit]=report
    return dict(schema='tennis-future-quality-report-v3', evaluated_at=stamp,period_complete=complete,
        completed=len(rows),pending_or_outside_completed_contract=pending,rejected=rejected,by_circuit=reports,
        status='eligible_for_independent_quality_review' if all(r['predeclared_statistical_gate_passed'] for r in reports.values()) else 'insufficient_confirmatory_predictive_evidence',
        predictive_quality_accredited=False, financial_validation=False, individual_certainty=False)
