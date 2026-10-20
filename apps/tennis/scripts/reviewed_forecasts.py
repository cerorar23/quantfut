"""Seal research forecasts from reviewed PDF cells and a fresh API calendar.

This is a research emission, not an official live-status or financial approval.
Uses the existing frozen hybrid without modifying its code or parameters.
"""
from pathlib import Path
import argparse,hashlib,json,re,sys
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pypdf import PdfReader
from tennis_engine.operations import utc,now
from tennis_engine.identities import normalized
from tennis_engine.model import ServeModel
from tennis_engine.research import hybrid_forecast
from tennis_engine.paper_validation import load_policy
from tennis_engine.state_capture import state

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):
 with Path(path).open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2,ensure_ascii=False,allow_nan=False)

def abbreviated_matches(short,full):
 """Exact surname plus all given initials, never a fuzzy acceptance threshold."""
 a,b=normalized(short).split(),normalized(full).split()
 if len(a)<2 or len(a)>len(b):return False
 initials=[]
 while a and len(a[0])==1:initials.append(a.pop(0))
 return bool(initials and a and len(b)>len(a) and b[-len(a):]==a and [word[0] for word in b[:-len(a)]]==initials)

def canonical_id(model,full):
 matches=[pid for pid,name in model.names.items() if normalized(name)==normalized(full)]
 if len(matches)!=1:raise ValueError('Full canonical name absent or ambiguous')
 return matches[0]

def cell_text(pdf,rect):
 """Extract only the reviewed rectangle; reject cross-court name coincidences."""
 if len(rect)!=4 or not all(isinstance(v,(int,float)) and not isinstance(v,bool) for v in rect) or not 0<=rect[0]<rect[2]<=1 or not 0<=rect[1]<rect[3]<=1:raise ValueError('Reviewed rectangle required')
 page=PdfReader(pdf).pages[0];width=float(page.mediabox.width);height=float(page.mediabox.height);parts=[]
 def visit(text,cm,tm,font,size):
  x=(tm[4]*cm[0]+tm[5]*cm[2]+cm[4])/width
  top=1-(tm[4]*cm[1]+tm[5]*cm[3]+cm[5])/height
  if rect[0]<=x<=rect[2] and rect[1]<=top<=rect[3]:parts.append(text)
 page.extract_text(visitor_text=visit)
 return normalized(' '.join(parts))

def verify_review(review,decision_at):
 receipt=json.loads(Path(review['receipt_path']).read_text(encoding='utf8'))
 if not receipt.get('accepted_document') or receipt['http_status']!=200 or sha(receipt['source_path'])!=receipt['sha256']:raise ValueError('Original official document required')
 if not utc(receipt['received_at'])<utc(decision_at) or (utc(decision_at)-utc(receipt['received_at'])).total_seconds()>900:raise ValueError('Official observation unavailable or stale')
 authority={'almaty_op':('https://www.protennislive.com/posting/2026/9410/op.pdf','ATP','11851','Asia/Almaty'),
 'brussels_op':('https://www.protennislive.com/posting/2026/7485/op.pdf','ATP','3669','Europe/Brussels'),
 'osaka_op':('https://wtafiles.wtatennis.com/pdf/draws/2026/405/OP.pdf','WTA','1666','Asia/Tokyo'),
 'ningbo_op':('https://wtafiles.wtatennis.com/pdf/draws/2026/2092/OP.pdf','WTA','10180','Asia/Shanghai')}
 expected=authority[review['source_label']]
 if (receipt['url'],review['circuit'],review['provider_tournament_id'],review['timezone'])!=expected:raise ValueError('Unreviewed authority, circuit or tournament binding')
 if review['date']!='2026-10-19':raise ValueError('This reviewed edition is restricted to 19 October 2026')
 document=normalized(' '.join(p.extract_text() for p in PdfReader(receipt['source_path']).pages))
 if not any(token in document for token in ('19 october 2026','october 19 2026')) or 'order of play' not in document:raise ValueError('Document date/title mismatch')
 text=cell_text(receipt['source_path'],review['rect'])
 if len(re.findall(r'\bvs\b',text))!=1 or any(not re.search(r'\b'+re.escape(normalized(name))+r'\b',text) for name in review['players']):raise ValueError('Exact opposing singles pair absent from reviewed cell')
 lower=datetime.fromisoformat(review['date']+'T'+review['official_earliest_local']).replace(tzinfo=ZoneInfo(review['timezone'])).astimezone(timezone.utc)
 if utc(decision_at)>=lower:raise ValueError('Earliest reviewed schedule bound elapsed; live verification required')
 return dict(source_path=receipt['source_path'],source_sha256=receipt['sha256'],receipt_path=review['receipt_path'],receipt_sha256=sha(review['receipt_path']),
  observed_at=receipt['received_at'],official_schedule_earliest=lower.isoformat(),timing_kind=review['timing_kind'],court=review['court'],rect=review['rect'],
  actual_start_verified=False,roof_state_verified=False,review_method='Visual PDF cell review plus exact extracted opposing names')

def eligible_event(review,rows,decision_at):
 proof=verify_review(review,decision_at)
 candidates=[]
 for row,receipt in rows:
  if str(row['tournament_key'])!=review['provider_tournament_id'] or row['event_date']!=review['date'] or str(row['tournament_season'])!='2026':continue
  expected='Atp Singles' if review['circuit']=='ATP' else 'Wta Singles'
  if row['event_type_type']!=expected:continue
  if not abbreviated_matches(row['event_first_player'],review['players'][0]) or not abbreviated_matches(row['event_second_player'],review['players'][1]):continue
  candidates.append((row,receipt))
 if len(candidates)!=1:raise ValueError('Unique same-orientation provider singles fixture required')
 row,receipt=candidates[0]
 if state(row['event_status'])!='scheduled_unverified' or row.get('event_live')!='0':raise ValueError('Provider reports live, ended, cancelled or unknown status')
 age=(utc(decision_at)-utc(receipt['received_at'])).total_seconds()
 if not 0<age<=900:raise ValueError('Provider calendar not available or stale')
 start=row['event_date']+'T'+row['event_time']+':00+00:00'
 if not utc(decision_at)<utc(start) or utc(start)<utc(proof['official_schedule_earliest']):raise ValueError('Provider estimate elapsed or precedes official schedule bound')
 if str(row['first_player_key'])==str(row['second_player_key']):raise ValueError('Provider identity conflict')
 return row,receipt,proof,start

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('evidence-root','review','policy','data-root','improvements-root','output'):p.add_argument('--'+name,type=Path,required=True)
 args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False);policy=load_policy(args.policy)
 # This research tool may be added without altering frozen core modules or models.
 if not all(sha(path)==value for path,value in policy['artifacts'].items()):raise ValueError('Frozen model changed')
 reviewed=json.loads(args.review.read_text(encoding='utf8'));rows=[];source_hashes={}
 for path in sorted((args.evidence_root/'state_capture/originals').glob('*/receipt.json')):
  receipt=json.loads(path.read_text(encoding='utf8'))
  if receipt['http_status']!=200 or sha(receipt['source_path'])!=receipt['sha256']:raise ValueError('Invalid provider archive')
  source_hashes[str(path.resolve())]=sha(path)
  rows.extend((row,receipt) for row in json.loads(Path(receipt['source_path']).read_text())['result'])
 models={c:ServeModel(args.data_root/'models'/(c+'_current'),uncertainty=False) for c in ('ATP','WTA')}
 decisions=[];forecasts=[]
 for review in reviewed:
  decision=now()
  try:
   event,receipt,proof,start=eligible_event(review,rows,decision);model=models[review['circuit']]
   a,b=[canonical_id(model,name) for name in review['players']]
   prediction=hybrid_forecast(args.data_root,args.data_root/'models'/(review['circuit']+'_current'),args.improvements_root/(review['circuit']+'_pool/pool.json'),a,b,'Hard')
   # Recheck freshness/start after computation; never backdate sealing to decision.
   sealed=now();eligible_event(review,rows,sealed)
   unknown=prediction['serve']['unknown_effects']
   if unknown:raise ValueError('Player/surface parameters missing in frozen model')
   forecasts.append(dict(provider_event_id=str(event['event_key']),circuit=review['circuit'],tournament=event['tournament_name'],
    players=review['players'],canonical_players=[a,b],provider_player_ids=[str(event['first_player_key']),str(event['second_player_key'])],
    scheduled_start_estimate=start,prediction_sealed_at=sealed,official_schedule=proof,
    calendar_receipt_path=str((Path(receipt['source_path']).parent/'receipt.json').resolve()),calendar_source_sha256=receipt['sha256'],
    prediction=prediction,predictive_contract='Conditional on completed match; winner-only research',
    unused_context=['daily_load','exact_rest','spatial','weather'],research_forecast=True,betting_recommendation=False,financial_validation=False,production_approved=False))
   decisions.append(dict(players=review['players'],status='research_forecast_sealed'))
  except (ValueError,KeyError,TypeError,OSError) as error:decisions.append(dict(players=review['players'],status='excluded',reason=str(error)))
 payload=dict(schema='tennis-reviewed-research-forecast-batch-v1',created_at=now(),policy_sha256=sha(args.policy),
  review_path=str(args.review.resolve()),review_sha256=sha(args.review),emitter_sha256=sha(__file__),
  frozen_model_artifacts=policy['artifacts'],candidate_code_sha256=policy['candidate_code_sha256'],
  calendar_receipt_sha256=source_hashes,forecasts=forecasts,decisions=decisions,
  reviewed=len(reviewed),emitted=len(forecasts),excluded=len(decisions)-len(forecasts),
  scope='Reviewed scheduled fixtures; not universal live status verification or evidence of profitability.',
  actual_wagers_placed=0,odds_credits=0,production_approved=False)
 body=json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
 write(args.output/'predictions.json',dict(payload,payload_sha256=hashlib.sha256(body).hexdigest()))
 print(json.dumps(dict(reviewed=len(reviewed),emitted=len(forecasts),excluded=len(decisions)-len(forecasts),production_approved=False)))

if __name__=='__main__':main()
