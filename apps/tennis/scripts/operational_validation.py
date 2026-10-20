"""Manual bounded operational checks. Never schedules work or places wagers."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
from collections import Counter
import argparse,hashlib,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tennis_engine.operations import now,utc
from tennis_engine.venues import VenueRegistry,load_seed
from tennis_engine.state_capture import StateStore,state
from tennis_engine.weather import capture_forecast,load_forecasts,forecast_features
from tennis_engine.paper_validation import freeze_paper_policy,load_policy,evaluate_paper,seal_paper_order,quote_receipt_from_archive


def write_new(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x',encoding='utf8') as f:json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False)

def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
 check=sub.add_parser('capture-weather',help='Bind fresh captured fixtures to reviewed venues, then one public weather request')
 for name in ['state-root','venue-seed','output']:check.add_argument('--'+name,type=Path,required=True)
 check.add_argument('--venue-base-seed',type=Path,action='append',default=[],help='Earlier immutable metadata revisions, oldest first')
 check.add_argument('--weather-receipt',type=Path,help='Reuse a validated archive without another request')
 freeze=sub.add_parser('freeze-paper')
 for name in ['model-protocol','output']:freeze.add_argument('--'+name,type=Path,required=True)
 freeze.add_argument('--start',required=True);freeze.add_argument('--end',required=True)
 seal=sub.add_parser('seal-paper')
 for name in ['policy','record','quote-receipt','orders']:seal.add_argument('--'+name,type=Path,required=True)
 seal.add_argument('--event-id',required=True);seal.add_argument('--selection',required=True)
 evaluate=sub.add_parser('evaluate-paper')
 for name in ['policy','orders','results','output']:evaluate.add_argument('--'+name,type=Path,required=True)
 evaluate.add_argument('--closings',type=Path)
 args=p.parse_args()
 if args.command=='freeze-paper':
  freeze_paper_policy(args.output,args.model_protocol,args.start,args.end);print(json.dumps(dict(policy=str(args.output),paper_only=True,production_approved=False)));return
 if args.command=='seal-paper':
  path=seal_paper_order(args.orders,args.record,args.event_id,args.selection,quote_receipt_from_archive(args.quote_receipt),args.policy)
  print(json.dumps(dict(order=str(path),paper_only=True,actual_execution_verified=False)));return
 if args.command=='evaluate-paper':
  inputs=[args.policy,args.results,*sorted(args.orders.glob('*.json'))]
  if args.closings:inputs.append(args.closings)
  before={str(path.resolve()):hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}
  closings=None
  if args.closings:
   closings=[dict(event_id=r['event_id'],receipt=quote_receipt_from_archive(Path(r['receipt_path']))) for r in json.loads(args.closings.read_text())]
  result=evaluate_paper(args.policy,args.orders,args.results,closings=closings)
  if any(hashlib.sha256(Path(path).read_bytes()).hexdigest()!=sha for path,sha in before.items()):raise ValueError('Evaluation input changed during computation')
  result['input_sha256']=before
  write_new(args.output,result)
  print(json.dumps(dict(status=result['status'],by_circuit=result['by_circuit'],production_approved=False)));return
 root=args.output;root.mkdir(parents=True,exist_ok=False)
 registry=VenueRegistry(root/'venues.sqlite')
 for seed in [*args.venue_base_seed,args.venue_seed]:load_seed(registry,seed)
 store=StateStore(args.state_root);decision=now();ids=[r[0] for r in store.db.execute('SELECT DISTINCT event_id FROM observations')]
 latest=[store.timeline(identity,decision)['latest'] for identity in ids];latest=[r for r in latest if r]
 rows=[json.loads(r['payload']) for r in latest]
 received=max(r['received_at'] for r in latest) if latest else decision
 if not rows:raise ValueError('Fresh state capture required')
 report=registry.enrich_calendar(rows,decision,input_timezone='UTC',source_received_at=received)
 write_new(root/'calendar_venues.json',report)
 venues={v['venue_resolution']['venue']['venue_id']:v['venue_resolution']['venue'] for v in report['events'] if v['venue_resolution']['status']=='resolved'}
 if not venues:raise ValueError('No verified venues available for weather request')
 receipt=args.weather_receipt or capture_forecast(root/'weather',list(venues.values()))
 available=max(r['available_at'] for r in load_forecasts(receipt));at=now();weather=[]
 indexed={str(r['event_key']):r for r in rows}
 for event in report['events']:
  raw=indexed[event['provider_event_id']];resolved=event['venue_resolution']
  if state(raw.get('event_status'))!='scheduled_unverified':continue
  if resolved['status']!='resolved':continue
  start=raw['event_date']+'T'+raw['event_time']+':00+00:00'
  if utc(start)<=utc(at):continue
  # Primary venue identity does not confirm individual-court roof state.
  venue=resolved['venue']
  roof=forecast_features(receipt,venue,start,at,'unknown')
  outdoor_candidate=forecast_features(receipt,venue,start,at,'open')
  weather.append(dict(provider_event_id=event['provider_event_id'],venue_id=venue['venue_id'],scheduled_start_estimate=start,
      provider_status=raw.get('event_status'),roof_state='unknown',actual_match_exposure=roof,
      outdoor_sensitivity_candidate=outdoor_candidate,candidate_is_actual_exposure=False))
 write_new(root/'weather_candidates.json',weather)
 state_summary=store.summary(at)
 result=dict(schema='tennis-operational-data-check-v1',checked_at=at,state_summary=state_summary,
  calendar_received_at=received,weather_available_at=available,weather_receipt=str(receipt.resolve()),
  venue_seed_sha256={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*args.venue_base_seed,args.venue_seed]},
  events=report['n_total'],with_reviewed_primary_venue=report['n_resolved'],with_primary_coordinates=report['n_with_coordinates'],
  unmatched_tournaments=dict(Counter(e['tournament_name'] for e in report['events'] if e['venue_resolution']['status']!='resolved')),
  forecast_points=len(venues),forecast_candidates=len(weather),candidate_statuses=dict(Counter(r['outdoor_sensitivity_candidate']['status'] for r in weather)),
  actual_roof_observations=0,feature_used_by_frozen_baseline=False,new_public_weather_requests=0 if args.weather_receipt else 1,
  cancelled_events_excluded_from_forecast_candidates=sum(state(r.get('event_status'))=='cancelled' for r in rows),
  new_odds_requests=0,odds_credits_consumed=0,provider_account_plan_or_quota_confirmed=False,
  pre_match_official_verification_required=True,production_approved=False,actual_wagers_placed=0)
 write_new(root/'report.json',result);print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
