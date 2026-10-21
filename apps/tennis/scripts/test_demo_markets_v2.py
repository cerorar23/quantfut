"""Bounded multi-event test on the separately authorized demo account.

At most 500 credits; separate ledger; primary account never read or charged.
Captures all observed supported keys across up to 30 books and twelve events.
"""
from pathlib import Path
import argparse,json,hashlib,sys,math
from datetime import timedelta
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tennis_engine.operations import Capture,now,utc
from tennis_engine.model import ServeModel
from tennis_engine.identities import normalized
from tennis_engine.scoring import Rules
from tennis_markets_v2 import MarketEngine
from tennis_markets_v2.offers import API_KEYS,price_offers
from tennis_markets_v2.account_identity import is_shared_key

RULES={'tennis_wta_ningbo_open','tennis_wta_osaka','tennis_wta_japan_open','tennis_wta_wuhan_open','tennis_atp_shanghai_masters','tennis_atp_almaty_open','tennis_atp_european_open','tennis_atp_brussels_open'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(path,value):
 with path.open('x',encoding='utf8') as f:json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False)

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('credential-file','data-root','output'):p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--approved-shared-account-test',action='store_true',help='Requires explicit user authorization for this key and 500-credit scope')
 args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False)
 values=dict(line.strip().split('=',1) for line in args.credential_file.read_text().splitlines() if '=' in line and not line.lstrip().startswith('#'))
 key=values['TENNIS_ODDS_API_KEY'].strip().strip(chr(34)).strip(chr(39))
 shared={}
 for name in ('.env.server','.env'):
  source=args.credential_file.parent/name
  if source.exists():shared.update(dict(line.strip().split('=',1) for line in source.read_text().splitlines() if '=' in line and not line.lstrip().startswith('#')))
 same=is_shared_key(key,shared)
 if same and not args.approved_shared_account_test:raise ValueError('This key is the shared account, not a separate demo; explicit authorization and central ledger reconciliation required')
 client=Capture(args.output/'operations',key,cap=500,account_reserve=0)
 report=dict(schema='tennis-demo-market-test-v2',started_at=now(),authorized_credit_cap=500,
  primary_account_used=same,separate_account=not same,primary_reserve_changed=False,actual_wagers_placed=0,production_approved=False,events=[],errors=[])
 models={};engines={}
 sports,receipt=client.request('sports');report['initial_quota_headers']=receipt['headers']
 active=[s['key'] for s in sports if s.get('active') and s['key'].startswith(('tennis_atp_','tennis_wta_')) and not s.get('has_outrights')]
 report['active_tennis_sports']=active;events=[]
 for sport in sorted(active)[:8]:
  fixtures,calendar=client.request('sports/'+sport+'/events')
  events.extend((event,calendar) for event in fixtures if utc(now())+timedelta(minutes=15)<utc(event['commence_time'])<utc(now())+timedelta(days=4))
 report['eligible_future_calendar_events']=len(events)
 for event,calendar in sorted(events,key=lambda x:x[0]['commence_time'])[:12]:
  item=dict(event=event,calendar_receipt=calendar,model_identity_status='unresolved',official_live_state_verified=False,executable=False)
  report['events'].append(item);prefix='sports/'+event['sport_key']+'/events/'+event['id']
  try:
   inventory,inventory_receipt=client.request(prefix+'/markets',dict(regions='eu,uk,us,us2,au'))
   if any(inventory.get(k)!=event.get(k) for k in ('id','sport_key','home_team','away_team','commence_time')):raise ValueError('Inventory identity differs')
   item['inventory_receipt']=inventory_receipt
   available={b['key']:{m['key'] for m in b.get('markets',[]) if m['key'] in API_KEYS} for b in inventory.get('bookmakers',[])}
   chosen=[];covered=set()
   while available and len(chosen)<30:
    book=max(available,key=lambda k:(len(available[k]-covered),len(available[k]),k));keys=available.pop(book)
    if keys:chosen.append(book);covered|=keys
   item.update(observed_market_keys=sorted(covered),bookmakers_requested=chosen)
   if not covered:
    item['status']='no_supported_market_keys';continue
   circuit='ATP' if event['sport_key'].startswith('tennis_atp_') else 'WTA'
   model_path=args.data_root/'models'/(circuit+'_current')
   if circuit not in models:models[circuit]=ServeModel(model_path,uncertainty=False)
   model=models[circuit];ids=[]
   for field in ('home_team','away_team'):
    matches=[pid for pid,name in model.names.items() if normalized(name)==normalized(event[field])]
    if len(matches)==1:ids.append(matches[0])
   engine=None
   if len(ids)==2 and event['sport_key'] in RULES:
    point=model.predict(*ids,'Hard',uncertainty=False)
    if not point['unknown_effects']:
     source=dict(event=event,circuit=circuit,canonical_players=ids,serve=point,model_path=str((model_path/'model.json').resolve()),
      model_sha256=sha(model_path/'model.json'),code_sha256={p.name:sha(p) for p in Path(__file__).resolve().parents[1].joinpath('tennis_markets_v2').glob('*.py')},
      prediction_sealed_at=now(),rules=dict(best_of=3,surface='Hard',scope='Reviewed tournament configuration; not physical court/roof confirmation'),
      scope='Coherent Markov market integration test; not a financial approval')
     path=args.output/('prediction_'+event['id']+'.json');write(path,source)
     item.update(model_identity_status='unique_exact_full_names',prediction_path=str(path.resolve()),prediction_sha256=sha(path))
     engine=MarketEngine(point['p'],point['q'],Rules(3))
   units=math.ceil(len(chosen)/10);spent=client.db.execute('SELECT coalesce(sum(cost),0) FROM charges WHERE month=?',(now()[:7],)).fetchone()[0]
   remaining=min(500-spent,client.remaining or 0);maximum=remaining//units
   requested=sorted(covered)[:maximum]
   item.update(requested_market_keys=requested,omitted_by_budget=sorted(covered-set(requested)))
   if not requested:
    item['status']='demo_budget_exhausted';break
   quoted,quote_receipt=client.request(prefix+'/odds',dict(bookmakers=','.join(chosen),markets=','.join(requested),oddsFormat='decimal'))
   if any(quoted.get(k)!=event.get(k) for k in ('id','sport_key','home_team','away_team','commence_time')):raise ValueError('Quote identity changed')
   item.update(status='observed',quote_receipt=quote_receipt,
    returned_market_keys=sorted({m['key'] for b in quoted.get('bookmakers',[]) for m in b.get('markets',[])}),
    returned_bookmakers=len(quoted.get('bookmakers',[])),outcomes_returned=sum(len(m.get('outcomes',[])) for b in quoted.get('bookmakers',[]) for m in b.get('markets',[])),
    offers=price_offers(quoted,engine,quote_receipt['received_at'],now()) if engine else [],
    unpriced_reason=None if engine else 'Identity, rules or model parameters not verified; quotes archived without fabricated probabilities')
  except (ValueError,RuntimeError,OSError,KeyError,TypeError) as error:
   item.update(status='stopped',error_type=type(error).__name__);report['errors'].append(dict(event_id=event['id'],type=type(error).__name__))
   if client.remaining is None:break
 report.update(completed_at=now(),budget=client.budget_report(now()[:7]),
  returned_market_keys=sorted({key for e in report['events'] for key in e.get('returned_market_keys',[])}),
  outcomes_returned=sum(e.get('outcomes_returned',0) for e in report['events']),
  priced_outcomes=sum(r['status']=='priced_research' for e in report['events'] for r in e.get('offers',[])),
  priced_events=sum(bool(e.get('offers')) for e in report['events']))
 write(args.output/'report.json',report)
 print(json.dumps(dict(events=len(report['events']),priced_events=report['priced_events'],outcomes=report['outcomes_returned'],priced_outcomes=report['priced_outcomes'],market_keys=report['returned_market_keys'],budget=report['budget'])))

if __name__=='__main__':main()
