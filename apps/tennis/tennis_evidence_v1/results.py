"""Reconcile archived API results without inventing timestamps or identities."""
from collections import Counter, defaultdict
from pathlib import Path
import json
import re
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
from tennis_engine.operations import now, utc
from tennis_engine.paper_validation import digest
from tennis_engine.prospective import result_valid
from tennis_engine.state_capture import state
from tennis_quality_v3.prospective import load, read, write_new, checksum, evaluate_future
from tennis_allmarkets_v1.prospective import evaluate as evaluate_markets, load as load_markets


def completed_set(a: int, b: int) -> bool:
    return (max(a,b)==6 and min(a,b)<=4) or (max(a,b)==7 and min(a,b) in (5,6))


def score_text(scores: list[dict]) -> tuple[str,int]:
    """API 6.4 / 7.7 means games 6–7 and tie-break points 4–7, not floats."""
    if not isinstance(scores,list) or not scores:
        raise ValueError('No set-by-set score')
    ordered=sorted(scores,key=lambda x:int(x['score_set']))
    if [int(s['score_set']) for s in ordered]!=list(range(1,len(ordered)+1)):
        raise ValueError('Duplicate or noncontiguous set numbers')
    result=[];closed=0
    for s in ordered:
        parts=[re.fullmatch(r'(\d+)(?:\.(\d+))?',str(s[k])) for k in ('score_first','score_second')]
        if any(x is None for x in parts): raise ValueError('Unsupported score encoding')
        a,b=[int(x[1]) for x in parts]
        decimals=[x[2] for x in parts]
        suffix=''
        if any(v is not None for v in decimals):
            if any(v is None for v in decimals) or {a,b}!={6,7}:
                raise ValueError('Incomplete or misplaced tie-break points')
            points=list(map(int,decimals));winner=0 if a>b else 1
            if points[winner]<7 or points[winner]-points[1-winner]<2:
                raise ValueError('Tie-break points conflict with set winner')
            suffix=f'({points[1-winner]})'
        if closed!=len(result): raise ValueError('A partial set cannot precede another set')
        closed+=int(completed_set(a,b));result.append(f'{a}-{b}{suffix}')
    return ' '.join(result),closed


def timestamp_proof(review: dict, event_id: str, as_of: str) -> dict:
    """Only explicit, reviewed physical timestamps extracted from archived JSON.

    Field pointers bind values to original bytes. Semantic/source review is
    recorded explicitly; this is not an independent external attestation.
    """
    if review['event_id']!=event_id or review.get('semantics')!='physical_court_start_end' or review.get('reviewed') is not True or not review.get('reviewed_by'):
        raise ValueError('Explicit physical-time source review required')
    host=urlparse(review['source_url']).hostname
    if urlparse(review['source_url']).scheme!='https' or not any(host==h or str(host).endswith('.'+h) for h in ('atptour.com','wtatennis.com','itftennis.com','protennislive.com','api-tennis.com')):
        raise ValueError('Unrecognized timestamp source authority')
    if digest(review['source_path'])!=review['source_sha256']:
        raise ValueError('Timestamp source changed')
    raw=read(review['source_path'])
    if not isinstance(review.get('participants'),list) or len(review['participants'])!=2 or review['participants'][0]==review['participants'][1]:
        raise ValueError('Exact oriented source participants required')
    for field,expected in zip(('home_team','away_team'),review['participants']):
        value=raw
        pointer=review['field_paths'][field]
        if not isinstance(pointer,list) or not pointer:raise ValueError('Native participant JSON path required')
        for part in pointer:value=value[part]
        if value!=expected:raise ValueError('Timestamp source participants do not match reviewed pair')
    for field in ('actual_start','actual_end'):
        value=raw
        pointer=review['field_paths'][field]
        if not isinstance(pointer,list) or not pointer: raise ValueError('Native JSON field path required')
        for part in pointer:value=value[part]
        if not isinstance(value,str) or not (value.endswith('Z') or re.search(r'[+-]\d\d:\d\d$',value)) or utc(value)!=utc(review[field]):
            raise ValueError('Physical timestamp does not match original timezone-aware field')
    if not utc(review['actual_start'])<utc(review['actual_end'])<=utc(review['received_at'])<=utc(as_of):
        raise ValueError('Invalid physical timestamp chronology')
    return review


def provider_result(parent: dict, raw: dict, receipt: dict, original: dict, proof: dict|None, as_of: str) -> dict:
    """Exact provider IDs anchor orientation; abbreviations are never guessed."""
    event=parent['event'];identity=event['id'];metadata=parent['tournament_metadata']
    if identity!='api_tennis:'+str(raw['event_key']): raise ValueError('Different provider event')
    for field in ('first_player_key','second_player_key','tournament_key','tournament_season'):
        if str(raw[field])!=str(original[field]): raise ValueError('Provider identity/orientation/edition changed')
    terminal=state(raw.get('event_status'))
    if terminal not in ('completed','retired','walkover'): raise ValueError('No supported terminal result')
    if raw.get('event_type_type')!=('Atp Singles' if parent['circuit']=='ATP' else 'Wta Singles'):
        raise ValueError('Wrong circuit or doubles event')
    if not utc(parent['sealed_at'])<utc(receipt['received_at'])<=utc(as_of):
        raise ValueError('Terminal evidence unavailable after original forecast')
    a,b=event['home_team'],event['away_team']
    winner={'First Player':a,'Second Player':b}.get(raw.get('event_winner'))
    value=dict(event_id=identity,sport_key=event['sport_key'],home_team=a,away_team=b,
        status=terminal,official_winner=winner,best_of=metadata['best_of'],
        source_path=receipt['source_path'],source_sha256=receipt['sha256'],
        received_at=receipt['received_at'],actual_start=None,actual_end=None,completed_sets=0)
    if terminal!='walkover':
        value['score_A_B'],value['completed_sets']=score_text(raw.get('scores'))
        if winner is None: raise ValueError('Official winner missing')
        if terminal=='completed':
            sets=[tuple(map(int,m)) for m in re.findall(r'(\d+)-(\d+)',value['score_A_B'])]
            sa=sum(x>y for x,y in sets);sb=len(sets)-sa
            if re.sub(r'\s','',str(raw.get('event_final_result')))!=f'{sa}-{sb}':
                raise ValueError('Final sets disagree with score rows')
        if proof is None: raise ValueError('Physical start/end evidence still missing')
        proof=timestamp_proof(proof,identity,as_of)
        if proof['participants']!=[a,b]:raise ValueError('Physical times belong to another oriented pair')
        if not utc(proof['actual_end'])<=utc(receipt['received_at']):
            raise ValueError('Provider reported completion before physical end')
        value.update(actual_start=proof['actual_start'],actual_end=proof['actual_end'],
            received_at=max((receipt['received_at'],proof['received_at']),key=utc),
            physical_time_review=proof,physical_times_are_scheduled_estimates=False)
    if not result_valid(value): raise ValueError('Result does not satisfy frozen result contract')
    if terminal!='walkover' and not utc(parent['sealed_at'])<utc(value['actual_start']):
        raise ValueError('Original prediction was not before physical start')
    if terminal!='walkover' and parent['fixture_receipt'].get('official_not_before') and utc(value['actual_start'])<utc(parent['fixture_receipt']['official_not_before']):
        raise ValueError('Physical start conflicts with original official minimum; review required')
    return value


def reconcile(quality_protocol: Path, market_protocol: Path, capture_root: Path, times_root: Path, output_root: Path) -> dict:
    """One offline pass; exclusive outputs and unchanged frozen evaluators."""
    protocol=load(quality_protocol);load_markets(market_protocol);at=now()
    parents_root=Path(quality_protocol).parent/'future_predictions'
    if not parents_root.is_dir() or not Path(capture_root).is_dir() or not Path(times_root).is_dir():
        raise ValueError('Existing forecast, capture and explicit timestamp-review roots required')
    output=Path(output_root);output.mkdir(parents=True,exist_ok=False)
    parents={};originals={};invalid=[]
    for path in sorted(parents_root.glob('*.json')):
        try:
            v=read(path);sha=v.pop('payload_sha256')
            if checksum(v)!=sha or v['protocol_sha256']!=digest(quality_protocol) or v['artifacts']!=protocol['artifacts']: raise ValueError('Changed forecast')
            identity=v['event']['id']
            if identity in parents: raise ValueError('Duplicate forecast event')
            fixture=v['fixture_receipt'];raw_path=Path(fixture['calendar_source_path'])
            if digest(raw_path)!=fixture['calendar_source_sha256']:raise ValueError('Original forecast calendar changed')
            original=[r for r in read(raw_path)['result'] if 'api_tennis:'+str(r['event_key'])==identity]
            if len(original)!=1: raise ValueError('Unique original provider identity required')
            parents[identity]=v;originals[identity]=original[0]
        except (ValueError,KeyError,TypeError,OSError) as error:invalid.append(dict(path=str(path),reason=str(error)))
    observations=defaultdict(list);outside=set();inputs={};source_errors=[]
    for path in sorted((Path(capture_root)/'originals').glob('*/receipt.json')):
        try:
            receipt=read(path)
            if receipt.get('http_status')!=200 or receipt.get('method') not in ('get_fixtures','get_livescore'):continue
            if utc(receipt['received_at'])>utc(at):continue
            if digest(receipt['source_path'])!=receipt['sha256']:raise ValueError('Result archive source changed')
            inputs[str(path.resolve())]=digest(path);inputs[receipt['source_path']]=receipt['sha256']
            body=read(receipt['source_path'])
            if body.get('success')!=1 or not isinstance(body.get('result'),list):raise ValueError('Invalid provider response')
            event_ids=[str(row['event_key']) for row in body['result']]
            if len(set(event_ids))!=len(event_ids):raise ValueError('Duplicate provider event in one response')
            for raw in body['result']:
                identity='api_tennis:'+str(raw['event_key'])
                if state(raw.get('event_status')) in ('completed','retired','walkover','cancelled'):
                    if identity in parents:observations[identity].append((raw,receipt))
                    else:outside.add(identity)
        except (ValueError,KeyError,TypeError,OSError) as error:source_errors.append(dict(path=str(path),reason=str(error)))
    proofs=defaultdict(list)
    for path in sorted(Path(times_root).glob('*.json')):
        try:
            review=read(path);timestamp_proof(review,review['event_id'],at)
            inputs[str(path.resolve())]=digest(path);inputs[review['source_path']]=review['source_sha256']
            proofs[review['event_id']].append(review)
        except (ValueError,KeyError,TypeError,OSError,IndexError) as error:source_errors.append(dict(path=str(path),reason=str(error)))
    accepted=[];pending=[];candidates=[]
    for identity,parent in parents.items():
        rows=observations[identity]
        event=parent['event']
        entry=dict(event_id=identity,players=[event['home_team'],event['away_team']],
            estimated_start_utc=event['commence_time'],estimated_start_mexico=utc(event['commence_time']).astimezone(ZoneInfo('America/Mexico_City')).isoformat())
        if not rows:
            reason='scheduled_in_future' if utc(event['commence_time'])>utc(at) else 'awaiting_terminal_source'
            pending.append(dict(entry,reason=reason));continue
        signatures={json.dumps({k:raw.get(k) for k in ('event_status','event_winner','scores','event_final_result','first_player_key','second_player_key','tournament_key','tournament_season')},sort_keys=True) for raw,receipt in rows}
        if len(signatures)!=1:
            pending.append(dict(entry,reason='conflicting_terminal_sources_need_review'));continue
        evidence=proofs[identity]
        if len({(r['actual_start'],r['actual_end']) for r in evidence})>1:
            pending.append(dict(entry,reason='conflicting_physical_time_reviews'));continue
        raw,receipt=max(rows,key=lambda pair:utc(pair[1]['received_at']))
        try:
            value=provider_result(parent,raw,receipt,originals[identity],evidence[0] if evidence else None,at)
            if value['status']!='walkover' and not utc(protocol['evaluation_start'])<=utc(value['actual_start'])<utc(protocol['evaluation_end']):
                raise ValueError('Physical start outside frozen study interval')
            accepted.append(value)
        except (ValueError,KeyError,TypeError,OSError) as error:
            reason=str(error);pending.append(dict(entry,reason=reason))
            candidates.append(dict(entry,reason=reason,provider_observation=raw,receipt=receipt,
                actual_start=None,actual_end=None,scheduled_time_is_not_physical=True))
    write_new(output/'accepted_results.json',accepted);write_new(output/'terminal_candidates.json',candidates)
    quality=evaluate_future(quality_protocol,parents_root,output/'accepted_results.json')
    markets=evaluate_markets(market_protocol,Path(market_protocol).parent/'predictions',output/'accepted_results.json')
    write_new(output/'winner_evaluation.json',quality);write_new(output/'markets_evaluation.json',markets)
    starts=[utc(v['event']['commence_time']) for v in parents.values()]
    summary=dict(schema='tennis-result-reconciliation-v1',checked_at=at,registered_events=len(parents),
        admissible_results=len(accepted),pending=pending,pending_reasons=dict(Counter(r['reason'] for r in pending)),
        first_estimated_start=min(starts).isoformat() if starts else None,
        first_estimated_start_mexico=min(starts).astimezone(ZoneInfo('America/Mexico_City')).isoformat() if starts else None,
        hours_until_first_estimate=max(0,(min(starts)-utc(at)).total_seconds()/3600) if starts else None,
        matched_terminal_events=sum(bool(rows) for rows in observations.values()),unregistered_terminal_events=len(outside),
        invalid_forecasts=invalid,source_errors=source_errors,inputs=inputs,
        quality_accredited=False,profitability_accredited=False,new_api_requests=0,new_odds_credits=0)
    write_new(output/'reconciliation.json',summary)
    return summary
