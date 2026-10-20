"""Score sealed future forecasts against independently archived results."""
from collections import Counter,defaultdict
import json
import re
from pathlib import Path
from .context import source_valid
from .operations import utc
from .shadow import verify_record,verified_fixture,PHASES,capture_phase
from .normalize import standard_score
from .evaluate import scores
from .research import calibration_bins
from .ingest import save_json
from .operations import now
import hashlib


def freeze_protocol(data_root,improvements_root,calibration_root,output,start,end):
    output=Path(output)
    if output.exists():raise ValueError('A frozen protocol cannot be overwritten')
    created=now()
    if not utc(created)<utc(start)<utc(end):raise ValueError('Declare a genuinely future evaluation interval')
    assets={};required={}
    for circuit in ('ATP','WTA'):
        model=Path(data_root)/f'models/{circuit}_current'
        files=[model/'model.json',model/'precision.npz',model/'training_receipt.json',
               Path(improvements_root)/f'{circuit}_pool/pool.json',Path(improvements_root)/f'{circuit}_controls.json',
               Path(calibration_root)/f'{circuit}_calibration_v2/calibrators.json']
        hashes={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        assets.update(hashes);required[circuit]=list(hashes.values())
    protocol={'schema':'tennis-future-protocol-v1','created_at':created,'evaluation_start':start,'evaluation_end':end,
              'artifacts':assets,'required_artifact_hashes':required,'phases':list(PHASES),
              'candidate':'Static serve-return / Elo winner hybrid, with experimental exact-line marginal calibration',
              'references':['calibrated_surface_elo','surface_elo','markov','same-time de-vig market where available'],
              'metrics':['log_loss','brier','calibration','dependence-aware uncertainty'],
              'sample_target_per_circuit':500,'sample_target_is_not_power_guarantee':True,
              'selection_rules':'No automatic wagers. Do not refit these candidates on this evaluation interval.',
              'retirements':'Retained in coverage and financial ledger; probability scores conditional on completed matches.',
              'production_approved':False,'financial_validation':False}
    save_json(output,protocol);return protocol


def result_valid(result):
    try:
        received=utc(result['received_at'])
        if result.get('status')=='walkover':
            return (not result.get('actual_start') and result.get('completed_sets')==0
                    and result.get('home_team')!=result.get('away_team') and source_valid(result,result['received_at']))
        start=utc(result['actual_start']);ended=utc(result['actual_end'])
        if not start<ended<=received or not source_valid(result,result['received_at']):return False
        if result['status'] not in ('completed','retired','disqualified','walkover'):return False
        if result['home_team']==result['away_team']:return False
        if result['status']=='completed':
            score=result['score_A_B']
            if not isinstance(score,str) or not score.split() or not all(re.fullmatch(r'\d+-\d+(?:\(\d+\))?',token) for token in score.split()):return False
            if result['best_of'] not in (3,5):return False
            tokens=re.findall(r'(\d+)-(\d+)(?:\(\d+\))?',score)
            reverse=' '.join(f'{b}-{a}' for a,b in tokens)
            if not (standard_score(score,result['best_of']) or standard_score(reverse,result['best_of'])):return False
            a_won=sum(int(a)>int(b) for a,b in tokens)>sum(int(b)>int(a) for a,b in tokens)
            expected=result['home_team'] if a_won else result['away_team']
            if result['official_winner']!=expected:return False
        return True
    except (ValueError,KeyError,TypeError):return False


def evaluate_prospective(operations_root,results_path,output,protocol_path=None):
    results=json.loads(Path(results_path).read_text(encoding='utf-8'))
    if not isinstance(results,list):raise ValueError('Results must be a list')
    protocol=json.loads(Path(protocol_path).read_text(encoding='utf-8')) if protocol_path else None
    if len({r['event_id'] for r in results})!=len(results):raise ValueError('Duplicate result identity')
    indexed={r['event_id']:r for r in results};rejected=Counter();candidates={};status=Counter(r.get('status','unknown') for r in results)
    for path in sorted((Path(operations_root)/'shadow').rglob('record.json')):
        try:record=verify_record(path)
        except (ValueError,OSError,KeyError):rejected['invalid_record_hash']+=1;continue
        for row in record.get('events',[]):
            event=row['event'];result=indexed.get(event['id']);prediction=row.get('prediction')
            if not result:continue
            if not result_valid(result):rejected['invalid_result_evidence']+=1;continue
            if result['status']!='completed':rejected['outside_completed_match_probability_contract']+=1;continue
            sealed=record.get('prediction_sealed_at');phase=row.get('capture_phase')
            if not sealed or phase not in PHASES:rejected['unsealed_or_outside_predeclared_window']+=1;continue
            if capture_phase(event['commence_time'],sealed)!=phase:
                rejected['incorrect_capture_phase']+=1;continue
            if protocol:
                if not (utc(protocol['created_at'])<=utc(sealed)<utc(result['actual_start'])
                        and utc(protocol['evaluation_start'])<=utc(result['actual_start'])<utc(protocol['evaluation_end'])):
                    rejected['outside_frozen_protocol_period']+=1;continue
                observed=set(row.get('artifact_sha256',{}).values())
                if row.get('calibration_artifact'):observed.add(row['calibration_artifact']['sha256'])
                if not set(protocol['required_artifact_hashes'][row['circuit']]).issubset(observed):
                    rejected['different_model_or_calibration_version']+=1;continue
            if any(result.get(k)!=event.get(k) for k in ('sport_key','home_team','away_team')):
                rejected['result_event_mismatch']+=1;continue
            if not prediction or utc(sealed)>=utc(result['actual_start']):rejected['not_before_start']+=1;continue
            import math
            values=[prediction.get('winner_A')]+[prediction[k] for k in ('markov_A','surface_elo_A','calibrated_surface_elo_A') if prediction.get(k) is not None]
            if any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) or not 0<=v<=1 for v in values):
                rejected['invalid_probability']+=1;continue
            if not row.get('identities',{}).get('identities_verified') or not verified_fixture(event,row.get('fixture_receipt'),sealed)['eligible']:
                rejected['unverified_pre_match_observation']+=1;continue
            key=(event['id'],phase)
            candidate={'event_id':event['id'],'phase':phase,'circuit':row['circuit'],'sealed_at':sealed,
                       'record_path':str(path),'result_source':result['source_path'],
                       'y':int(result['official_winner']==event['home_team']),
                       'hybrid':prediction['winner_A'],'markov':prediction.get('markov_A'),
                       'surface_elo':prediction.get('surface_elo_A'),
                       'calibrated_surface_elo':prediction.get('calibrated_surface_elo_A')}
            if key not in candidates or utc(sealed)<utc(candidates[key]['sealed_at']):candidates[key]=candidate
    groups=defaultdict(list)
    for row in candidates.values():groups[(row['circuit'],row['phase'])].append(row)
    metrics={}
    for (circuit,phase),rows in groups.items():
        metrics[circuit+'_'+phase]={}
        for model in ('hybrid','markov','surface_elo','calibrated_surface_elo'):
            valid=[r for r in rows if r.get(model) is not None]
            if valid:
                y=[r['y'] for r in valid];p=[r[model] for r in valid]
                metrics[circuit+'_'+phase][model]={'scores':scores(y,p),'calibration':calibration_bins(y,p)}
    report={'schema':'tennis-prospective-evaluation-v1','scored_event_windows':len(candidates),
            'protocol':str(protocol_path) if protocol_path else None,
            'distinct_scored_events':len({r['event_id'] for r in candidates.values()}),
            'results_by_status':dict(status),'rejections':dict(rejected),'metrics':metrics or None,
            'rows':list(candidates.values()),'production_approved':False,'financial_validation':False,
            'limits':['Each event is counted separately per phase, never as independent repeated bets.',
                      'Probability evaluation is conditional on completed matches; retired results remain in coverage.',
                      'No ROI is inferred. Financial evaluation must use the full settlement ledger.',
                      'Local hashes are not an independent timestamp attestation.']}
    save_json(output,report);return report


def clv(entry,closing,actual_start,max_close_age_seconds=1800):
    identity=('event_id','sport_key','market','selection','line','description','settlement_contract')
    if any(entry.get(k)!=closing.get(k) for k in identity) or not entry.get('settlement_contract'):
        return {'status':'incomparable_contract_or_line','clv':None}
    try:
        start=utc(actual_start);captured=utc(closing['captured_at']);updated=utc(closing['last_update'])
        placed=utc(entry['captured_at'])
        if not placed<=captured<=start or not updated<=captured or (start-captured).total_seconds()>max_close_age_seconds or (start-updated).total_seconds()>max_close_age_seconds:
            return {'status':'not_verified_close','clv':None}
        odd=float(entry['decimal_odds']);close_odd=float(closing['decimal_odds']);fair=float(closing['de_vig_probability_no_push'])
        import math
        if not all(math.isfinite(x) for x in (odd,close_odd,fair)) or min(odd,close_odd)<=1 or not 0<fair<1:raise ValueError()
        return {'status':'comparable_pre_start_close','price_ratio_clv':odd/close_odd-1,
                'no_vig_closing_return_no_push':odd*fair-1,'financial_profit':None,
                'limit':'Closing reference value is not realized profit; integer lines are conditional on no push'}
    except (KeyError,TypeError,ValueError):return {'status':'invalid_close_data','clv':None}
