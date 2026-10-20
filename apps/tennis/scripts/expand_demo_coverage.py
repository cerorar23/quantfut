"""Use the authorized remainder of one demo account for bookmaker coverage.

Each account's original ledger is reused; confirmed total cannot exceed 500.
New bookmaker coverage is prioritized; subsequent snapshots preserve changes.
"""
from pathlib import Path
import argparse,json,sys
from collections import defaultdict,Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tennis_engine.operations import now,utc
from tennis_markets_v2.demo_budget import DemoCapture
from tennis_markets_v2.offers import API_KEYS
from tennis_markets_v2.account_identity import is_shared_key

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--credential-file',type=Path,required=True);p.add_argument('--account-root',type=Path,required=True)
 p.add_argument('--approved-shared-account-test',action='store_true')
 args=p.parse_args();original=json.loads((args.account_root/'report.json').read_text())
 values=dict(line.strip().split('=',1) for line in args.credential_file.read_text().splitlines() if '=' in line and not line.lstrip().startswith('#'))
 shared={}
 for name in ('.env.server','.env'):
  source=args.credential_file.parent/name
  if source.exists():shared.update(dict(line.strip().split('=',1) for line in source.read_text().splitlines() if '=' in line and not line.lstrip().startswith('#')))
 if is_shared_key(values['TENNIS_ODDS_API_KEY'],shared) and not args.approved_shared_account_test:raise ValueError('Supplied key is the shared account; explicit account-specific authorization required')
 client=DemoCapture(args.account_root/'operations',values['TENNIS_ODDS_API_KEY'].strip())
 if client.db.execute('SELECT coalesce(sum(cost),0) FROM charges WHERE month=?',(now()[:7],)).fetchone()[0]>=500:raise ValueError('Authorized500 credits already consumed; no request sent')
 _,initial=client.request('sports');start=int(initial['headers']['x-requests-used'])
 seen=defaultdict(set)
 for entry in original['events']:seen[entry['event']['id']].update(entry.get('bookmakers_requested',[]))
 snapshots=[];errors=[]
 def spent():return client.db.execute('SELECT coalesce(sum(cost),0) FROM charges WHERE month=?',(now()[:7],)).fetchone()[0]
 for cycle in range(8):
  if spent()>=500 or not client.remaining:break
  for entry in original['events']:
   if spent()>=500 or not client.remaining:break
   event=entry['event']
   if utc(event['commence_time'])<=utc(now()):continue
   prefix='sports/'+event['sport_key']+'/events/'+event['id']
   try:
    inventory,inv_receipt=client.request(prefix+'/markets',dict(regions='eu,uk,us,us2,au'))
    if any(inventory.get(k)!=event.get(k) for k in ('id','sport_key','home_team','away_team','commence_time')):raise ValueError('Changed event; retain source without mapping')
    keys={b['key']:{m['key'] for m in b.get('markets',[]) if m['key'] in API_KEYS} for b in inventory.get('bookmakers',[])}
    books=sorted([b for b in keys if keys[b]],key=lambda b:(b in seen[event['id']],-len(keys[b]),b))
    item=dict(cycle=cycle,event_id=event['id'],inventory_receipt=inv_receipt,quotes=[]);snapshots.append(item)
    for offset in range(0,len(books),10):
     allowance=min(500-spent(),client.remaining or 0)
     if allowance<=0:break
     group=books[offset:offset+10];markets=sorted(set().union(*(keys[b] for b in group)))[:allowance]
     if not markets:continue
     quoted,receipt=client.request(prefix+'/odds',dict(bookmakers=','.join(group),markets=','.join(markets),oddsFormat='decimal'))
     comparable=all(quoted.get(k)==event.get(k) for k in ('id','sport_key','home_team','away_team','commence_time'))
     item['quotes'].append(dict(receipt=receipt,bookmakers_requested=group,markets_requested=markets,
       event_identity_comparable=comparable,returned_bookmakers=[b['key'] for b in quoted.get('bookmakers',[])],
       returned_market_keys=sorted({m['key'] for b in quoted.get('bookmakers',[]) for m in b.get('markets',[])}),
       outcomes=sum(len(m.get('outcomes',[])) for b in quoted.get('bookmakers',[]) for m in b.get('markets',[]))))
     seen[event['id']].update(group)
   except (ValueError,RuntimeError,OSError,KeyError,TypeError) as error:
    errors.append(dict(event_id=event['id'],type=type(error).__name__))
    if client.remaining is None:break
  if client.remaining is None:break
 final=dict(schema='tennis-demo-expanded-coverage-v2',completed_at=now(),authorized_cap=500,primary_account_used=False,
  prior_account_used_header=start,snapshots=snapshots,errors=errors,budget=client.budget_report(now()[:7]),
  bookmaker_count_by_event={k:len(v) for k,v in seen.items()},extra_outcomes=sum(q['outcomes'] for s in snapshots for q in s['quotes']),
  prospective_forecast=False,financial_validation=False,actual_wagers_placed=0,production_approved=False)
 target=args.account_root/'expanded_coverage.json'
 with target.open('x',encoding='utf8') as f:json.dump(final,f,indent=2)
 print(json.dumps(dict(budget=final['budget'],extra_outcomes=final['extra_outcomes'],bookmaker_count_by_event=final['bookmaker_count_by_event'],errors=len(errors))))

if __name__=='__main__':main()
