"""Prospective paper selections tied to archived quotes and frozen model files.

No wagering endpoint. Paper returns are not account executions or evidence of
future profitability. Missing results and closing prices remain in coverage.
"""
from collections import Counter,defaultdict
from datetime import datetime,timezone
import hashlib,json,math
from pathlib import Path
from typing import Any
import numpy as np
from .operations import utc,now,quote_gate
from .shadow import verify_record,verified_fixture,metadata_gate
from .prospective import result_valid,clv
from .settlement import settle,PINNACLE_RULE
from .benchmark import probability_metrics


def digest(path:Path)->str:return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical(value:Any)->bytes:return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def _number(value:Any,low:float,high:float)->bool:return not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value) and low<=value<=high

def freeze_paper_policy(path:Path,model_protocol:Path,start:str,end:str,*,created_at:str|None=None)->dict:
    stamp=created_at or now();protocol=json.loads(Path(model_protocol).read_text())
    if not utc(stamp)<utc(start)<utc(end):raise ValueError('A genuinely future paper interval is required')
    for p,s in protocol['artifacts'].items():
        if digest(p)!=s:raise ValueError('Frozen model artifact changed')
    policy=dict(schema='tennis-paper-financial-policy-v1',created_at=stamp,evaluation_start=start,evaluation_end=end,
        model_protocol_path=str(Path(model_protocol).resolve()),model_protocol_sha256=digest(model_protocol),
        candidate_code_sha256={p.name:digest(p) for p in sorted(Path(__file__).parent.glob('*.py'))},
        artifacts=protocol['artifacts'],required_artifact_hashes=protocol['required_artifact_hashes'],
        markets=['h2h'],bookmakers=['pinnacle'],rule_id=PINNACLE_RULE,features_used=[],
        selection='one_per_event_earliest_sealed_order_positive_conditional_model_return',
        minimum_conditional_return=0.,flat_paper_units=1.,commission_rate=0.,per_order_cost_units=0.,
        costs_are_declared_simulation_assumptions=True,max_quote_age_seconds=900,max_close_age_seconds=1800,
        minimum_events_per_circuit=500,minimum_competitions_per_circuit=30,bootstrap_draws=1000,bootstrap_seed=20261019,
        minimum_counts_are_not_power_guarantees=True,calibration_selection_on_this_interval=False,
        paper_only=True,actual_execution_verified=False,production_approved=False)
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf8') as f:json.dump(policy,f,indent=2)
    return policy

def load_policy(path:Path)->dict:
    p=json.loads(Path(path).read_text(encoding='utf8'))
    if p.get('schema')!='tennis-paper-financial-policy-v1' or p.get('paper_only') is not True:raise ValueError('Frozen paper policy required')
    if not utc(p['created_at'])<utc(p['evaluation_start'])<utc(p['evaluation_end']):raise ValueError('Invalid policy chronology')
    if digest(p['model_protocol_path'])!=p['model_protocol_sha256']:raise ValueError('Model protocol changed')
    if p['markets']!=['h2h'] or p['bookmakers']!=['pinnacle'] or p['rule_id']!=PINNACLE_RULE:raise ValueError('Unsupported financial study contract')
    if p['features_used']:raise ValueError('This policy evaluates the frozen baseline without unvalidated context')
    if any(Path(f).name!=f or digest(Path(__file__).parent/f)!=s for f,s in p['candidate_code_sha256'].items()):raise ValueError('Frozen active candidate code changed')
    for name in ('flat_paper_units','minimum_events_per_circuit','minimum_competitions_per_circuit','bootstrap_draws'):
        if not _number(p[name],1,10000):raise ValueError('Invalid policy sample/stake parameter')
    if not _number(p['commission_rate'],0,1) or not _number(p['per_order_cost_units'],0,100):raise ValueError('Invalid declared costs')
    return p

def quote_receipt_from_archive(path:Path)->dict:
    """Adapt the existing Odds API archive without trusting copied prices/times."""
    path=Path(path);receipt=json.loads(path.read_text(encoding='utf8'))
    request=receipt['path']
    import re
    if not re.fullmatch(r'sports/tennis_(?:atp|wta)_[^/]+/(?:events/[^/]+/)?odds',request):raise ValueError('Current tennis odds archive required; historical/catalogue snapshots are not eligible')
    source=path.parent/'response.json'
    if digest(source)!=receipt['sha256']:raise ValueError('Original quote response differs from archive receipt')
    return dict(source_path=str(source.resolve()),sha256=receipt['sha256'],requested_at=receipt['requested_at'],received_at=receipt['received_at'],
        archive_receipt_path=str(path.resolve()),archive_receipt_sha256=digest(path))

def _quote(receipt:dict,event:dict,selection:str)->tuple[dict,dict,dict]:
    """Read and bind actual returned price, not a caller's copied odds field."""
    original=quote_receipt_from_archive(Path(receipt['archive_receipt_path']))
    if original!=receipt:raise ValueError('Quote receipt differs from original archive')
    raw=Path(receipt['source_path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=receipt['sha256']:raise ValueError('Quote archive changed')
    if utc(receipt['requested_at'])>utc(receipt['received_at']):raise ValueError('Invalid quote chronology')
    body=json.loads(raw);events=body if isinstance(body,list) else [body]
    matches=[x for x in events if x.get('id')==event['id']]
    if len(matches)!=1:raise ValueError('Unique matching quoted event required')
    quoted=matches[0]
    if any(quoted.get(k)!=event.get(k) for k in ('sport_key','home_team','away_team','commence_time')):raise ValueError('Quote identity/schedule differs')
    books=[b for b in quoted.get('bookmakers',[]) if b.get('key')=='pinnacle']
    if len(books)!=1:raise ValueError('Unique Pinnacle quote required')
    markets=[m for m in books[0].get('markets',[]) if m.get('key')=='h2h']
    if len(markets)!=1:raise ValueError('Unique H2H market required')
    outcomes=markets[0]['outcomes'];names={event['home_team'],event['away_team']}
    if len(outcomes)!=2 or {o['name'] for o in outcomes}!=names or selection not in names:raise ValueError('Complete complementary winner market required')
    if any(not _number(o.get('price'),1.00000001,10000) or o.get('point') is not None for o in outcomes):raise ValueError('Invalid winner quote')
    return books[0],markets[0],next(o for o in outcomes if o['name']==selection)

def assess_paper_event(row:dict,receipt:dict,decision_at:str,policy:dict,selection:str)->dict:
    """Technical readiness for this variant; unused context cannot block baseline."""
    event=row['event'];decision=utc(decision_at);reasons=[]
    if not utc(policy['created_at'])<decision or not utc(policy['evaluation_start'])<=utc(event['commence_time'])<utc(policy['evaluation_end']):reasons.append('outside_frozen_paper_period')
    if row.get('circuit') not in ('ATP','WTA') or not row.get('identities',{}).get('identities_verified'):reasons.append('unverified_circuit_or_identity')
    reasons.extend(verified_fixture(event,row.get('fixture_receipt'),decision_at)['reasons'])
    reasons.extend(metadata_gate(event,row.get('tournament_metadata')))
    prediction=row.get('prediction') or {};values=(prediction.get('winner_A'),prediction.get('winner_B'))
    if not all(_number(v,0,1) for v in values) or abs(sum(v for v in values if isinstance(v,(int,float)))-1)>1e-9:reasons.append('invalid_winner_probability')
    try:
        if utc(prediction['cutoff']+'T00:00:00Z')>decision:reasons.append('model_cutoff_after_decision')
        assets=dict(row.get('artifact_sha256') or {})
        if row.get('calibration_artifact'):assets[row['calibration_artifact']['path']]=row['calibration_artifact']['sha256']
        required=set(policy['required_artifact_hashes'][row['circuit']])
        if not required.issubset(set(assets.values())):reasons.append('model_version_not_frozen')
        if any(digest(p)!=s for p,s in assets.items()):reasons.append('model_artifact_changed')
        book,market,outcome=_quote(receipt,event,selection)
        reasons.extend(quote_gate(event,book,market,receipt['received_at'],decision_at,True,row.get('fixture_receipt'),policy['max_quote_age_seconds'])['reasons'])
    except (ValueError,KeyError,TypeError,OSError):return dict(paper_eligible=False,real_money_eligible=False,reasons=sorted(set(reasons+['invalid_archived_quote_or_model'])))
    side='A' if selection==event['home_team'] else 'B';probability=prediction.get('winner_'+side)
    expected=None if not _number(probability,0,1) else probability*outcome['price']-1
    if expected is None or expected<=policy['minimum_conditional_return']:reasons.append('below_predeclared_paper_selection_threshold')
    return dict(paper_eligible=not reasons,real_money_eligible=False,reasons=sorted(set(reasons)),decimal_odds=outcome['price'],selection_side=side,
        conditional_model_return=expected,ignored_unvalidated_context=['weather','daily_load','spatial'],actual_execution_verified=False)

def seal_paper_order(root:Path,record_path:Path,event_id:str,selection:str,quote_receipt:dict,policy_path:Path,*,decision_at:str|None=None)->Path:
    stamp=decision_at or now();policy=load_policy(policy_path);record=verify_record(record_path)
    sealed=record.get('prediction_sealed_at')
    if sealed is None or utc(sealed)>utc(quote_receipt['requested_at']) or utc(sealed)>=utc(stamp):raise ValueError('Prediction must be sealed before quote request and decision')
    rows=[r for r in record['events'] if r['event']['id']==event_id]
    if len(rows)!=1:raise ValueError('Unique sealed event required')
    row=rows[0];gate=assess_paper_event(row,quote_receipt,stamp,policy,selection)
    if not gate['paper_eligible']:raise ValueError('Paper event blocked: '+','.join(gate['reasons']))
    event=row['event'];identity=hashlib.sha256((digest(policy_path)+':'+event_id).encode()).hexdigest()
    order=dict(schema='tennis-sealed-paper-order-v1',event=event,event_id=event_id,circuit=row['circuit'],selection=selection,
        selection_side=gate['selection_side'],decimal_odds=gate['decimal_odds'],stake=policy['flat_paper_units'],bookmaker='pinnacle',market='h2h',
        rule_id=policy['rule_id'],sealed_at=stamp,prediction_sealed_at=sealed,record_path=str(Path(record_path).resolve()),record_sha256=digest(record_path),
        policy_path=str(Path(policy_path).resolve()),policy_sha256=digest(policy_path),quote_receipt=quote_receipt,
        competition_id=event['sport_key']+':'+str(utc(event['commence_time']).year),paper_only=True,actual_execution_verified=False)
    wrapped=dict(order,payload_sha256=hashlib.sha256(canonical(order)).hexdigest())
    root=Path(root);root.mkdir(parents=True,exist_ok=True);target=root/(identity+'.json')
    with target.open('x',encoding='utf8') as f:json.dump(wrapped,f,indent=2)
    return target

def _interval(rows:list[dict],field:str,policy:dict)->list[float]|None:
    groups=defaultdict(list)
    for r in rows:
        if r.get(field) is not None:groups[r['competition_id']].append(r)
    if len(groups)<2:return None
    blocks=list(groups.values());rng=np.random.default_rng(policy['bootstrap_seed']);values=[]
    for _ in range(policy['bootstrap_draws']):
        sample=[r for i in rng.integers(0,len(blocks),len(blocks)) for r in blocks[i]]
        values.append(sum(r[field] for r in sample)/sum(r['stake'] for r in sample))
    return np.quantile(values,[.025,.975]).tolist()

def evaluate_paper(policy_path:Path,orders_root:Path,results_path:Path,*,closings:list[dict]|None=None,as_of:str|None=None)->dict:
    policy=load_policy(policy_path);stamp=as_of or now();decision=utc(stamp)
    results=json.loads(Path(results_path).read_text(encoding='utf8'))
    if not isinstance(results,list) or len({r['event_id'] for r in results})!=len(results):raise ValueError('Unique independently archived results required')
    indexed={r['event_id']:r for r in results};closing_map={}
    for c in closings or []:
        if c['event_id'] in closing_map:raise ValueError('Duplicate closing event')
        closing_map[c['event_id']]=c['receipt']
    rows=[];rejected=Counter();seen=set()
    for path in sorted(Path(orders_root).glob('*.json')):
        try:
            order=json.loads(path.read_text(encoding='utf8'));checksum=order.pop('payload_sha256')
            if hashlib.sha256(canonical(order)).hexdigest()!=checksum or order['policy_sha256']!=digest(policy_path) or not order['paper_only']:raise ValueError()
            event=order['event'];event_id=order['event_id']
            if event_id in seen:raise ValueError('Duplicate sealed order')
            seen.add(event_id)
            if digest(order['record_path'])!=order['record_sha256'] or utc(order['sealed_at'])>decision:raise ValueError()
            original=verify_record(order['record_path']);candidates=[r for r in original['events'] if r['event']['id']==event_id]
            if (len(candidates)!=1 or candidates[0]['event']!=event or candidates[0]['circuit']!=order['circuit']
                or order['bookmaker']!='pinnacle' or order['market']!='h2h'
                or order['competition_id']!=event['sport_key']+':'+str(utc(event['commence_time']).year)
                or original.get('prediction_sealed_at')!=order['prediction_sealed_at']
                or not utc(order['prediction_sealed_at'])<=utc(order['quote_receipt']['requested_at'])<utc(order['sealed_at'])):raise ValueError()
            if not assess_paper_event(candidates[0],order['quote_receipt'],order['sealed_at'],policy,order['selection'])['paper_eligible']:raise ValueError()
            _,entry_market,quote=_quote(order['quote_receipt'],event,order['selection'])
            if order['decimal_odds']!=quote['price'] or order['stake']!=policy['flat_paper_units'] or order['rule_id']!=policy['rule_id'] or order['selection_side']!=('A' if order['selection']==event['home_team'] else 'B'):raise ValueError()
        except (ValueError,TypeError,KeyError,OSError):rejected['invalid_order_evidence']+=1;continue
        row=dict(event_id=event_id,circuit=order['circuit'],competition_id=order['competition_id'],stake=order['stake'],net_profit=None,clv_units=None,status='pending_result',
            model_probability=candidates[0]['prediction']['winner_'+order['selection_side']],
            entry_market_probability=(1/quote['price'])/sum(1/o['price'] for o in entry_market['outcomes']),completed_match_outcome=None)
        rows.append(row);result=indexed.get(event_id)
        try:
            if not result:continue
            if not result_valid(result) or utc(result['received_at'])>decision:raise ValueError('Invalid or not-yet-available result')
            if result['status']!='walkover' and result.get('official_winner') not in (event['home_team'],event['away_team']):raise ValueError('Unverified winner')
            if any(result.get(k)!=event.get(k) for k in ('home_team','away_team','sport_key')):raise ValueError('Result identity differs')
            timing=result.get('actual_start') or event['commence_time']
            if not utc(policy['evaluation_start'])<=utc(timing)<utc(policy['evaluation_end']) or utc(order['sealed_at'])>=utc(timing):raise ValueError('Not prospective')
            outcome=settle(dict(bet_id=event_id,bookmaker='pinnacle',market='h2h',rule_id=policy['rule_id'],placed_at=order['sealed_at'],
                stake=order['stake'],decimal_odds=order['decimal_odds'],selection=order['selection_side'],match_status=result['status'],completed_sets=result['completed_sets'],
                official_winner='A' if result.get('official_winner')==event['home_team'] else 'B',best_of=result.get('best_of',3)))
            if outcome['profit'] is None:continue
            row.update(status=outcome['status'],net_profit=outcome['profit']-max(0.,outcome['profit'])*policy['commission_rate']-policy['per_order_cost_units'])
            if result['status']=='completed':row['completed_match_outcome']=int(result['official_winner']==order['selection'])
            if result.get('actual_start') and event_id in closing_map:
                receipt=closing_map[event_id];book,market,selected=_quote(receipt,event,order['selection'])
                implied=sum(1/o['price'] for o in market['outcomes']);fair=(1/selected['price'])/implied
                close=dict(event_id=event_id,sport_key=event['sport_key'],market='h2h',selection=order['selection'],line=None,description=None,settlement_contract=policy['rule_id'],
                    captured_at=receipt['received_at'],last_update=market.get('last_update') or book['last_update'],decimal_odds=selected['price'],de_vig_probability_no_push=fair)
                entry=dict(close,captured_at=order['sealed_at'],decimal_odds=order['decimal_odds'])
                value=clv(entry,close,result['actual_start'],policy['max_close_age_seconds'])
                if value['status']=='comparable_pre_start_close':row['clv_units']=order['stake']*value['no_vig_closing_return_no_push']
        except (ValueError,KeyError,TypeError,OSError):rejected['invalid_result_or_close_evidence']+=1
    summaries={}
    for circuit in ('ATP','WTA'):
        all_rows=[r for r in rows if r['circuit']==circuit];complete=[r for r in all_rows if r['net_profit'] is not None];close=[r for r in all_rows if r['clv_units'] is not None]
        profit_ci=_interval(complete,'net_profit',policy);close_ci=_interval(close,'clv_units',policy)
        probabilities=[r for r in complete if r['completed_match_outcome'] is not None]
        metrics={k:probability_metrics([r['completed_match_outcome'] for r in probabilities],[r[c] for r in probabilities]) for k,c in [('model','model_probability'),('same_time_no_vig_market','entry_market_probability')]} if probabilities else None
        summaries[circuit]=dict(orders=len(all_rows),settled=len(complete),pending=len(all_rows)-len(complete),retirements_excluded=False,
            net_paper_roi=None if not complete else sum(r['net_profit'] for r in complete)/sum(r['stake'] for r in complete),net_paper_roi_ci95=profit_ci,
            closing_coverage=0. if not all_rows else len(close)/len(all_rows),closing_return_ci95=close_ci,
            competitions=len({r['competition_id'] for r in complete}),completed_match_probability_metrics=metrics,
            predeclared_evidence_gate=bool(decision>=utc(policy['evaluation_end']) and not rejected and len(complete)==len(all_rows)>=policy['minimum_events_per_circuit'] and len(close)==len(all_rows)
                and len({r['competition_id'] for r in complete})>=policy['minimum_competitions_per_circuit'] and profit_ci and profit_ci[0]>0 and close_ci and close_ci[0]>0))
    return dict(schema='tennis-paper-financial-report-v1',total_order_files=len(list(Path(orders_root).glob('*.json'))),valid_orders=len(rows),evaluated_at=stamp,policy_sha256=digest(policy_path),rows=rows,by_circuit=summaries,
        rejected=dict(rejected),paper_only=True,actual_execution_verified=False,production_approved=False,evaluation_period_complete=decision>=utc(policy['evaluation_end']),
        status='candidate_for_execution_review' if all(s['predeclared_evidence_gate'] for s in summaries.values()) else 'insufficient_prospective_financial_evidence',
        limits=['Paper prices are observed, not fills; account availability, limits, slippage and actual costs remain unverified.',
            'Block intervals are descriptive and do not capture all cross-tournament player dependence.',
            'One predeclared evaluation; repeated peeking or changing selection rules invalidates confirmatory interpretation.'])
