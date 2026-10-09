"""Bounded lifecycle for an existing sealed paper cohort; no operational bets."""
from collections import defaultdict
from datetime import UTC, datetime, timedelta
import json
import math
from pathlib import Path
import re
import sqlite3
from zoneinfo import ZoneInfo
import httpx

from .audit import Ledger, digest, write_json
from .context import utc
from .event_listing import _NextData
from .odds_capture import BoundedOddsCapture, prop_pairs
from .paper import score_result, summarize_scores, verify_registration
from .public_capture import capture


def now_utc():
    return datetime.now(UTC)


def portable_path(value):
    """Interpret either separator without rewriting a sealed document."""
    return Path(str(value).replace('\\','/'))


def official_metadata(raw, receipt, as_of):
    url=receipt['url']
    match=re.fullmatch(r'https://www\.nba\.com/game/([a-z]{2,3}-vs-[a-z]{2,3}-(002\d{7}))(?:/box-score)?',url)
    if not match or receipt['http_status']!=200 or utc(receipt['first_received_at_utc'])>utc(as_of):
        raise ValueError('received official regular game page required')
    from hashlib import sha256
    if sha256(raw).hexdigest()!=receipt['raw_sha256']:raise ValueError('official raw hash mismatch')
    parser=_NextData();parser.feed(raw.decode('utf8'))
    if len(parser.blocks)!=1:raise ValueError('one official embedded document required')
    game=json.loads(parser.blocks[0])['props']['pageProps']['game']
    if game['gameId']!=match[2] or game['gameStatus'] not in (1,2,3):raise ValueError('official game identity/state mismatch')
    sides={}
    for side in ('homeTeam','awayTeam'):
        team=game[side]
        if type(team['teamId']) is not int or team['teamId']<=0 or game[side+'Id']!=team['teamId']:
            raise ValueError('official team ID mismatch')
        sides[side]=dict(id=team['teamId'],name=team['teamCity']+' '+team['teamName'])
    if sides['homeTeam']['id']==sides['awayTeam']['id']:raise ValueError('distinct official teams required')
    return dict(nba_game_id=game['gameId'],game_slug=match[1],game_status=game['gameStatus'],
        tipoff_utc=utc(game['gameTimeUTC']).isoformat(),home_team=sides['homeTeam']['name'],away_team=sides['awayTeam']['name'],
        home_nba_team_id=sides['homeTeam']['id'],away_nba_team_id=sides['awayTeam']['id'],
        official_url=url,raw_sha256=receipt['raw_sha256'],first_received_at_utc=receipt['first_received_at_utc']),game


def load_cohort(path):
    path=portable_path(path);cohort=json.loads(path.read_bytes());seen=set();cache={};groups=defaultdict(list)
    for row in cohort['rows']:
        source=portable_path(row['registration'])
        if digest(source/'seal.json')!=row['registration_seal_sha256']:raise ValueError('cohort registration seal mismatch')
        if str(source) not in cache:cache[str(source)]=verify_registration(source)
        key=(row['event_id'],row['player_id'],row['market'])
        if key in seen:raise ValueError('duplicate cohort unit')
        seen.add(key)
        matches=[f for f in cache[str(source)] if (f['event_id'],f['player_id'],f['market'])==key]
        if len(matches)!=1 or matches[0]['sealed_at_utc']!=row['sealed_at_utc']:raise ValueError('unproven cohort prediction')
        groups[row['event_id']].append(dict(matches[0],registration=source.as_posix()))
    if len(seen)!=cohort['units']:raise ValueError('cohort count mismatch')
    for event,rows in groups.items():
        sources={r['registration'] for r in rows}
        if len(sources)!=1:raise ValueError('one preregistered source per event required')
        source=next(iter(sources))
        source_keys={(f['player_id'],f['market']) for f in cache[str(Path(source))] if f['event_id']==event}
        if source_keys!={(f['player_id'],f['market']) for f in rows}:raise ValueError('cohort event subset differs from registered evaluation')
    return groups


def build_plan(cohort_path, receipts_path, raw_folder, output):
    groups=load_cohort(cohort_path);cut=now_utc();official=[];raw_folder=Path(raw_folder)
    for receipt in json.loads(Path(receipts_path).read_bytes()):
        raw=raw_folder/receipt['raw_sha256']
        metadata,_=official_metadata(raw.read_bytes(),receipt,cut.isoformat())
        metadata['raw_path']=raw.as_posix();official.append(metadata)
    if len({r['nba_game_id'] for r in official})!=len(official):raise ValueError('duplicate official event source')
    mappings=[];jobs=[]
    for event,rows in sorted(groups.items()):
        ref=rows[0]
        matches=[r for r in official if (r['home_team'],r['away_team'],utc(r['tipoff_utc']))==
            (ref['home_team'],ref['away_team'],utc(ref['tipoff_utc']))]
        if len(matches)!=1:raise ValueError('exact official teams and tipoff mapping required')
        mapped=dict(matches[0],provider_event_id=event,registration=ref['registration'],players=sorted({r['player_id'] for r in rows}),
            units=len(rows),identity_verified=True,known_at_original_prediction_seal=all(utc(matches[0]['first_received_at_utc'])<=utc(r['sealed_at_utc']) for r in rows),availability_final_verified=False,
            tipoff_mexico=utc(ref['tipoff_utc']).astimezone(ZoneInfo('America/Mexico_City')).isoformat())
        if any(utc(r['sealed_at_utc'])>=utc(mapped['tipoff_utc']) for r in rows):raise ValueError('post-start forecast')
        mappings.append(mapped);tip=utc(mapped['tipoff_utc'])
        jobs.append(dict(id=event+':pregame',kind='pregame',event_id=event,due=(tip-timedelta(minutes=2)).isoformat(),expires=tip.isoformat()))
        if any(r['hypothetical_entry']['selected'] for r in rows):
            jobs.append(dict(id=event+':close',kind='close',event_id=event,due=(tip-timedelta(minutes=2)).isoformat(),expires=tip.isoformat(),maximum_paid_credits=2))
        for hours in (4,6,12,24):
            jobs.append(dict(id=event+f':result:{hours}',kind='result',event_id=event,due=(tip+timedelta(hours=hours)).isoformat(),expires=(tip+timedelta(hours=hours+2)).isoformat()))
    maxcredits=sum(j.get('maximum_paid_credits',0) for j in jobs)
    if maxcredits>2:raise ValueError('this bounded lifecycle permits one closing event and two total credits')
    inputs={str(cohort_path):digest(cohort_path),str(receipts_path):digest(receipts_path)}
    inputs.update({r['raw_path']:r['raw_sha256'] for r in mappings})
    inputs.update({r['registration']+'/seal.json':digest(Path(r['registration'])/'seal.json') for r in mappings})
    plan=dict(version='nba-paper-lifecycle-1',created_at_utc=cut.isoformat(),cohort_path=str(cohort_path),input_hashes=inputs,
        unique_units=sum(len(r) for r in groups.values()),mappings=mappings,jobs=sorted(jobs,key=lambda j:(j['due'],j['kind'])),
        total_closing_credit_cap=maxcredits,automatic_retries=False,maximum_jobs_per_run=3,
        availability_policy='Only explicit Available in official game or explicit inactives/Out; roster, Active and missing report remain unknown; no guaranteed future health',
        closing_policy='Same book/event/player/market/line; new receipt in final five minutes; source and receipt age<=60s; hypothetical reference only',
        result_policy='Official final NBA boxscore; exact identity/time; DNP separate; no overwritten predictions; four bounded final checks',
        scientific_confirmation='not opened; descriptive cohort only',production_ready=False,periodic_copies=False)
    root=Path(output);root.mkdir(parents=True,exist_ok=False)
    write_json(root/'plan.json',plan)
    write_json(root/'seal.json',dict(plan_sha256=digest(root/'plan.json'),external_anchor=False))
    return plan


def verify_plan(folder):
    root=Path(folder);seal=json.loads((root/'seal.json').read_bytes())
    if digest(root/'plan.json')!=seal['plan_sha256']:raise ValueError('lifecycle plan changed')
    plan=json.loads((root/'plan.json').read_bytes())
    for path,hashed in plan['input_hashes'].items():
        if digest(portable_path(path))!=hashed:raise ValueError('lifecycle input changed')
    load_cohort(plan['cohort_path'])
    return plan


def availability_review(game, mapping, receipt, targets):
    cut=utc(receipt['first_received_at_utc']);tip=utc(mapping['tipoff_utc']);rows=[]
    if game['gameStatus']!=1 or not tip-timedelta(minutes=5)<=cut<tip:
        return dict(status='not_current_pregame_window',rows=[],availability_final_verified=False)
    members={};inactives=set()
    for side in ('homeTeam','awayTeam'):
        for p in game[side].get('players',[]):
            if p['personId'] in members:raise ValueError('duplicate official event player')
            members[p['personId']]=p
        inactives.update(p['personId'] for p in game[side].get('inactives',[]))
    for pid in targets:
        player=members.get(pid);raw=player.get('status') if player else None
        state='official_inactive' if pid in inactives else 'explicit_available_observed' if raw=='Available' else 'explicit_out_observed' if raw=='Out' else 'unknown'
        rows.append(dict(player_id=pid,state=state,status_raw=raw,listed=bool(player),
            evidence_sha256=receipt['raw_sha256'],first_received_at_utc=receipt['first_received_at_utc'],
            final_future_participation_guaranteed=False,available_observed=state=='explicit_available_observed'))
    return dict(status='current_official_observation',rows=rows,availability_final_verified=False,
        available_observed=sum(r['available_observed'] for r in rows),unknown=sum(r['state']=='unknown' for r in rows),actionable=False)


def compare_close(forecast, quotes, decision):
    entry=forecast['hypothetical_entry'];ref=forecast['reference_quote'];cut=utc(decision);tip=utc(forecast['tipoff_utc'])
    matches=[q for q in quotes if all(q.get(k)==ref.get(k) for k in ('event_id','book','market','provider_player_name','line'))]
    if not entry['selected']:return dict(comparable=False,reason='not_a_preregistered_paper_entry')
    if len(matches)!=1:return dict(comparable=False,reason='same_contract_closing_pair_absent_or_ambiguous')
    q=matches[0];received=utc(q['first_received_at_utc']);updated=utc(q['source_updated_at_utc'])
    if not (utc(forecast['sealed_at_utc'])<received<=cut<tip and tip-timedelta(minutes=5)<=received
            and updated<=received and max((cut-received).total_seconds(),(cut-updated).total_seconds())<=60):
        return dict(comparable=False,reason='not_fresh_pregame_close')
    over,under=q['over_decimal'],q['under_decimal']
    if any(isinstance(p,bool) or not isinstance(p,(int,float)) or not math.isfinite(p) or p<=1 for p in (over,under)):
        raise ValueError('valid closing prices required')
    side=entry['side'];closing=q[side+'_decimal'];total=1/over+1/under;prob=(1/closing)/total
    return dict(comparable=True,book=q['book'],market=q['market'],line=q['line'],side=side,
        entry_decimal=entry['decimal'],closing_decimal=closing,raw_price_clv=entry['decimal']/closing-1,
        closing_overround=total-1,closing_proportional_no_vig_probability=prob,
        hypothetical_no_vig_mark=entry['decimal']*prob-1,raw_sha256=q['raw_sha256'],
        closing_received_at_utc=q['first_received_at_utc'],real_account_contract_verified=False,operational_profit_proved=False)


def _closing_capture(root,mapping,forecasts,key):
    selected=[f for f in forecasts if f['hypothetical_entry']['selected']]
    books={f['reference_quote']['book'] for f in selected};markets={f['market'] for f in selected}
    if len(books)!=1 or len(markets)>2:raise ValueError('one book/two market closing budget required')
    with httpx.Client(timeout=25,follow_redirects=False) as client:
        cap=BoundedOddsCapture(root/'raw',key,2,client=client)
        cap.request('account.json','sports',{},0)
        if now_utc()>=utc(mapping['tipoff_utc']):return dict(status='missed_pregame_window',credits=0,comparisons=[])
        payload=cap.request('close.json',f"sports/basketball_nba/events/{mapping['provider_event_id']}/odds",
            dict(bookmakers=','.join(sorted(books)),markets=','.join(sorted(markets)),dateFormat='iso',oddsFormat='decimal'),len(markets))
        if payload is None:return dict(status='close_not_received',credits=cap.meta['charged_credits'],reserved=cap.meta['reserved_credits'],comparisons=[])
        if (payload.get('sport_key')!='basketball_nba'
                or utc(payload['commence_time'])!=utc(mapping['tipoff_utc'])
                or {b['key'] for b in payload.get('bookmakers',[])}-books
                or any(m['key'] not in markets for b in payload.get('bookmakers',[]) for m in b.get('markets',[]))):
            raise ValueError('closing source sport/book scope mismatch')
        receipt=cap.meta['files'][-1]
        expected=dict(odds_api_event_id=mapping['provider_event_id'],home_team=mapping['home_team'],away_team=mapping['away_team'],scheduled_utc=mapping['tipoff_utc'])
        pairs,rejected=prop_pairs(payload,receipt,expected,receipt['first_received_at_utc'],historical=False)
        cut=now_utc().isoformat()
        comparisons=[dict(compare_close(f,pairs,cut),player_id=f['player_id'],market=f['market']) for f in selected]
        return dict(status='close_received',credits=cap.meta['charged_credits'],comparisons=comparisons,rejected=rejected)


def advance(plan_folder,state_path,output,key=None):
    """Run only due bounded jobs. Claim before requests; uncertain jobs never retry."""
    plan=verify_plan(plan_folder);groups=load_cohort(plan['cohort_path']);cut=now_utc()
    state=Ledger(state_path);state.verify();plan_hash=digest(Path(plan_folder)/'plan.json')
    with sqlite3.connect(state.path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS claims (job_key TEXT PRIMARY KEY,claimed_at TEXT NOT NULL)')
        db.executescript("CREATE TRIGGER IF NOT EXISTS claims_no_delete BEFORE DELETE ON claims BEGIN SELECT RAISE(ABORT,'immutable job claim'); END; CREATE TRIGGER IF NOT EXISTS claims_no_update BEFORE UPDATE ON claims BEGIN SELECT RAISE(ABORT,'immutable job claim'); END;")
        payloads=[json.loads(row[0]) for row in db.execute("SELECT payload FROM events WHERE kind='job_result'")]
    payloads=[p for p in payloads if p.get('plan_sha256')==plan_hash]
    completed={p['event_id'] for p in payloads if p.get('status')=='scored'}
    scoring_paths=[p['evaluation'] for p in payloads if p.get('status')=='scored']
    root=Path(output);root.mkdir(parents=True,exist_ok=False);executed=[]
    for job in plan['jobs']:
        if utc(job['due'])>cut:continue
        if (cut<utc(job['expires']) and job['event_id'] not in completed
                and sum(bool(r.get('network_attempted')) for r in executed)>=plan['maximum_jobs_per_run']):
            break  # Leave remaining jobs unclaimed for a subsequent invocation in their window.
        job_key=plan_hash+':'+job['id']
        with sqlite3.connect(state.path) as db:
            db.execute('BEGIN IMMEDIATE')
            claimed=db.execute('INSERT OR IGNORE INTO claims VALUES (?,?)',(job_key,cut.isoformat())).rowcount
        if not claimed:continue
        state.append('job_claimed',dict(job_id=job['id'],job_key=job_key,before_network=True))
        if job['event_id'] in completed and job['kind']=='result':
            result=dict(status='already_scored',job_id=job['id'],event_id=job['event_id'])
        elif cut>=utc(job['expires']):
            result=dict(status='missed_window',job_id=job['id'],event_id=job['event_id'])
        else:
            if len([r for r in executed if r.get('network_attempted')])>=plan['maximum_jobs_per_run']:
                # Keep this claim explicit rather than silently issuing excess requests.
                result=dict(status='run_limit_requires_review',job_id=job['id'],event_id=job['event_id'])
            else:
                mapping=next(r for r in plan['mappings'] if r['provider_event_id']==job['event_id'])
                folder=root/(job['id'].replace(':','_'));folder.mkdir()
                result=dict(job_id=job['id'],event_id=job['event_id'],network_attempted=True)
                try:
                    if job['kind']=='close':
                        if not key:result.update(status='credentials_absent',network_attempted=False)
                        else:result.update(_closing_capture(folder,mapping,groups[job['event_id']],key))
                    else:
                        url=mapping['official_url'].removesuffix('/box-score')+('/box-score' if job['kind']=='result' else '')
                        receipt=capture(folder/'source',url,{url})
                        write_json(folder/'source_receipt.json',receipt)
                        raw=folder/'source/blobs'/receipt['raw_sha256']
                        metadata,game=official_metadata(raw.read_bytes(),receipt,now_utc().isoformat())
                        if any(metadata[k]!=mapping[k] for k in ('nba_game_id','home_team','away_team','tipoff_utc')):
                            raise ValueError('current official mapping changed')
                        if job['kind']=='pregame':
                            review=availability_review(game,mapping,receipt,mapping['players']);write_json(folder/'availability.json',review)
                            result.update(status='pregame_observed',review=review)
                        elif game['gameStatus']!=3:result.update(status='awaiting_final_result')
                        else:
                            result_dir=folder/'received';result_dir.mkdir();(result_dir/'boxscore.html').write_bytes(raw.read_bytes())
                            write_json(result_dir/'receipt.json',dict(receipt,game_id=mapping['nba_game_id'],raw_file='boxscore.html'))
                            evaluation=folder/'evaluation'
                            scored=score_result(mapping['registration'],job['event_id'],result_dir/'receipt.json',evaluation)
                            result.update(status='scored',evaluation=evaluation.as_posix(),metrics=scored)
                            completed.add(job['event_id']);scoring_paths.append(evaluation.as_posix())
                except (ValueError,KeyError,TypeError,OSError) as error:
                    result.update(status='source_or_validation_failure',error_type=type(error).__name__)
                write_json(folder/'job_result.json',result)
        result['plan_sha256']=plan_hash
        state.append('job_result',result);executed.append(result)
    if scoring_paths:
        summary=summarize_scores(scoring_paths,root/'summary')
    else:summary=None
    all_results=payloads+executed
    closing=[dict(event_id=p['event_id'],**comparison) for p in all_results
             if p.get('status')=='close_received' for comparison in p.get('comparisons',[])]
    closes=[p for p in all_results if ':close' in p.get('job_id','')]
    close_summary=dict(entries_compared=sum(r['comparable'] for r in closing),comparisons=closing,
        statuses=[dict(event_id=p['event_id'],status=p['status']) for p in closes],
        charged_credits=sum(p.get('credits',0) for p in closes),
        budget_reserved_for_uncertain_attempt=any(p['status'] in ('source_or_validation_failure','close_not_received') for p in closes),
        account_rules_verified=False,production_ready=False)
    write_json(root/'close_summary.json',close_summary)
    next_due=min((utc(j['due']) for j in plan['jobs'] if utc(j['due'])>cut),default=None)
    result=dict(as_of=cut.isoformat(),executed=executed,official_events_mapped=len(plan['mappings']),
        completed_events=len(completed),target_events=len(plan['mappings']),status='completed' if len(completed)==len(plan['mappings']) else 'waiting_for_due_windows_or_official_results',
        next_due_utc=next_due.isoformat() if next_due else None,summary=summary,closing=close_summary,state=state.verify(),
        total_future_closing_credit_cap=plan['total_closing_credit_cap'],operational_bets=0,production_ready=False)
    write_json(root/'result.json',result)
    return result
