"""One bounded live market integration check, up to 14 Odds API credits.

Uses the shared tennis ledger and 2,000/month cap, preserving 6,000 reserve.
Diagnostic observations only, no wagers or official live-state certification.
"""
from pathlib import Path
import argparse,json,hashlib,sys
from datetime import timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tennis_engine.operations import Capture,now,utc
from tennis_engine.model import ServeModel
from tennis_engine.identities import normalized
from tennis_engine.scoring import Rules
from tennis_markets_v2 import MarketEngine
from tennis_markets_v2.offers import API_KEYS,price_offers

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('workspace','engine-data','operations-root','output'):p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--approved-one-off',action='store_true',help='Explicit user authorization: <=14 credits, absolute balance floor 5104; does not change general reserve')
 args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False)
 if args.approved_one_off:
  claim=args.operations_root/'markets_v2_user_approval_20261019.claim.json'
  with claim.open('x',encoding='utf8') as f:json.dump(dict(authorization='Explicit user reply: single test <=14 credits, minimum balance 5104',claimed_at=now(),output=str(args.output.resolve())),f)
 values={}
 for filename in ('.env.server','.env'):
  path=args.workspace/filename
  if path.exists():
   values.update(dict(line.strip().split('=',1) for line in path.read_text().splitlines() if '=' in line and not line.lstrip().startswith('#')))
 key=values.get('TENNIS_ODDS_API_KEY') or values.get('ODDS_API_KEY')
 if not key:raise ValueError('Local Odds API credential missing; no request sent')
 key=key.strip().strip(chr(34)).strip(chr(39))
 client=Capture(args.operations_root,key,cap=2000,account_reserve=6000)
 report=dict(schema='tennis-real-markets-integration-v2',started_at=now(),max_run_credits=14,
  monthly_cap=2000,shared_account_reserve=6000,official_live_state_verified=False,actual_wagers_placed=0,production_approved=False)
 start_spent=client.db.execute('SELECT coalesce(sum(cost),0) FROM charges WHERE month=?',(now()[:7],)).fetchone()[0]
 if args.approved_one_off:
  client.cap=min(2000,start_spent+14);client.reserve=5104
  report.update(one_off_user_authorized=True,one_off_minimum_balance=5104,general_reserve_changed=False)
 try:
  sports,_=client.request('sports');models={};events=[]
  active=[s['key'] for s in sports if s.get('active') and s['key'].startswith(('tennis_atp_','tennis_wta_')) and not s.get('has_outrights')]
  report['active_tennis_sports']=active
  for sport in sorted(active)[:3]:
   fixtures,receipt=client.request('sports/'+sport+'/events')
   events.extend((e,receipt) for e in fixtures)
  report['free_calendar_events']=len(events)
  candidates=[]
  for event,calendar in events:
   if not utc(now())+timedelta(hours=1)<utc(event['commence_time'])<utc(now())+timedelta(days=3):continue
   circuit='ATP' if event['sport_key'].startswith('tennis_atp_') else 'WTA'
   if circuit not in models:models[circuit]=ServeModel(args.engine_data/'models'/(circuit+'_current'),uncertainty=False)
   model=models[circuit]
   names=[]
   for side in ('home_team','away_team'):
    matches=[pid for pid,name in model.names.items() if normalized(name)==normalized(event[side])]
    if len(matches)!=1:break
    names.append(matches[0])
   if len(names)!=2:continue
   point=model.predict(*names,'Hard',uncertainty=False)
   if point['unknown_effects']:continue
   candidates.append((event,calendar,names,point))
  if not candidates:
   report['stop_reason']='no_future_fixture_with_unambiguous_model_identity'
   raise ValueError('No sufficiently future unambiguous fixture for diagnostic capture')
  event,calendar,names,point=min(candidates,key=lambda e:e[0]['commence_time'])
  selected_circuit='ATP' if event['sport_key'].startswith('tennis_atp_') else 'WTA'
  model_path=args.engine_data/'models'/(selected_circuit+'_current')/'model.json'
  sealed=dict(event=event,canonical_players=names,serve=point,model_path=str(model_path.resolve()),
   model_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest(),sealed_at=now(),official_live_state_verified=False)
  with (args.output/'prediction_before_quote.json').open('x',encoding='utf8') as f:json.dump(sealed,f,indent=2)
  report.update(prediction_record_path=str((args.output/'prediction_before_quote.json').resolve()),
   prediction_record_sha256=hashlib.sha256((args.output/'prediction_before_quote.json').read_bytes()).hexdigest(),
   prediction_prequote_durable_seal_verified=True)
  prefix='sports/'+event['sport_key']+'/events/'+event['id']
  if client.remaining is None or client.remaining-1<client.reserve:
   report.update(stop_reason='shared_account_below_reserved_balance',candidate_event=event)
   raise ValueError('Preserve shared account reserve')
  inventory,inventory_receipt=client.request(prefix+'/markets',dict(regions='eu,uk,us,us2,au'))
  if any(inventory.get(k)!=event.get(k) for k in ('id','sport_key','home_team','away_team','commence_time')):raise ValueError('Inventory identity changed')
  available={b['key']:{m['key'] for m in b.get('markets',[]) if m['key'] in API_KEYS} for b in inventory.get('bookmakers',[])}
  chosen=[];covered=set()
  while available and len(chosen)<10:
   book=max(available,key=lambda key:(len(available[key]-covered),len(available[key]),key))
   markets=available.pop(book)
   if not markets:continue
   chosen.append(book);covered|=markets
  report.update(event=event,canonical_players=names,prediction_sealed_at=sealed['sealed_at'],serve=point,
   calendar_receipt=calendar,inventory_receipt=inventory_receipt,documented_api_keys=sorted(API_KEYS),
   observed_supported_market_keys=sorted(covered),not_observed_market_keys=sorted(API_KEYS-covered),bookmakers_requested=chosen)
  if covered:
   allowance=min(13,client.remaining-client.reserve,client.cap-client.db.execute('SELECT coalesce(sum(cost),0) FROM charges WHERE month=?',(now()[:7],)).fetchone()[0])
   priority=['h2h','h2h_s1','h2h_s2','spreads','totals','alternate_set_spreads','alternate_set_totals','spreads_s1','totals_s1','alternate_totals_s1','alternate_totals_s2','alternate_spreads','alternate_totals']
   requested=[key for key in priority if key in covered][:max(0,allowance)]
   report.update(requested_market_keys=requested,omitted_by_budget=sorted(covered-set(requested)))
   if not requested:raise ValueError('Insufficient approved one-off budget after inventory')
   quoted,receipt=client.request(prefix+'/odds',dict(bookmakers=','.join(chosen),markets=','.join(requested),oddsFormat='decimal'))
   if any(quoted.get(k)!=event.get(k) for k in ('id','sport_key','home_team','away_team','commence_time')):raise ValueError('Quoted identity changed')
   report.update(quote_receipt=receipt,offers=price_offers(quoted,MarketEngine(point['p'],point['q'],Rules(3)),receipt['received_at'],now()))
  report['status']='integration_observed' if covered else 'no_supported_markets_observed'
 except (ValueError,RuntimeError,OSError,KeyError,TypeError) as error:
  report.update(status='capture_stopped',error_type=type(error).__name__)
  # No raw exception text: upstream errors can include credential URLs.
 end_spent=client.db.execute('SELECT coalesce(sum(cost),0) FROM charges WHERE month=?',(now()[:7],)).fetchone()[0]
 report.update(completed_at=now(),run_reserved_credits=end_spent-start_spent,budget=client.budget_report(now()[:7]))
 with (args.output/'live_market_check.json').open('x',encoding='utf8') as f:json.dump(report,f,indent=2,ensure_ascii=False,allow_nan=False)
 print(json.dumps(dict(status=report['status'],market_keys=report.get('observed_supported_market_keys',[]),offers=len(report.get('offers',[])),budget=report['budget'])))

if __name__=='__main__':main()
