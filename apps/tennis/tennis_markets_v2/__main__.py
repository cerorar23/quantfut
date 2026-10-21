"""Export all-market research boards from sealed predictions or observed quotes."""
from pathlib import Path
import argparse,json,hashlib
from datetime import datetime,timezone
from collections import Counter
from tennis_engine.scoring import Rules
from .catalog import MarketEngine
from .offers import price_offers,API_KEYS

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--predictions',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 p.add_argument('--quotes',type=Path,help='JSON: original response_path and receipt_path; exact event identities required')
 args=p.parse_args();batch=json.loads(args.predictions.read_text(encoding='utf8'))
 payload=dict(batch);checksum=payload.pop('payload_sha256')
 if hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()!=checksum:raise ValueError('Original prediction batch hash differs')
 for path,value in batch['frozen_model_artifacts'].items():
  if sha(path)!=value:raise ValueError('Original model artifact changed')
 quote_event=quote_receipt=None
 if args.quotes:
  binding=json.loads(args.quotes.read_text());quote_receipt=json.loads(Path(binding['receipt_path']).read_text())
  if sha(binding['response_path'])!=quote_receipt['sha256']:raise ValueError('Original quote source changed')
  quote_event=json.loads(Path(binding['response_path']).read_text())
 if args.output.exists():raise ValueError('Output cannot overwrite an earlier export')
 rows=[];created=datetime.now(timezone.utc).isoformat()
 for row in batch['forecasts']:
  pred=row['prediction'];engine=MarketEngine(pred['serve']['p'],pred['serve']['q'],Rules(pred['best_of'],deciding_tiebreak=pred['deciding_tiebreak']))
  current=dict(provider_event_id=row['provider_event_id'],players=row['players'],scheduled_start_estimate=row['scheduled_start_estimate'],
   original_winner_sealed_at=row['prediction_sealed_at'],markets_derived_at=created,
   new_prospective_market_seal=False,original_snapshot_expanded_after_initial_seal=True,
   hybrid_winner_reference=dict(A=pred['winner_A'],B=pred['winner_B']),
   joint_model='Coherent uncalibrated MAP Markov; does not replace frozen hybrid winner',
   markets=engine.standard_board(),bookmaker_offers=[])
  if quote_event and [quote_event.get('home_team'),quote_event.get('away_team')]==row['players'] and quote_event['commence_time']==row['scheduled_start_estimate']:
   current['bookmaker_offers']=price_offers(quote_event,engine,quote_receipt['received_at'],created)
  rows.append(current)
 result=dict(schema='tennis-all-market-export-v2',created_at=created,source_predictions=str(args.predictions.resolve()),source_sha256=sha(args.predictions),
  code_sha256={p.name:sha(p) for p in Path(__file__).parent.glob('*.py')},events=rows,event_count=len(rows),
  probability_rows=sum(len(r['markets']) for r in rows),families=sorted({m['contract']['kind'] for r in rows for m in r['markets']}),
  documented_api_keys=sorted(API_KEYS),api_tennis_correct_score_or_tiebreak_keys_invented=False,
  calibration='Marginals uncalibrated; retrospective and future evaluation remain separate requirements',
  financial_validation=False,actual_wagers_placed=0,production_approved=False,
  limits=['Grid lines are illustrative mathematical contracts, not observed offers.',
   'Expanded after original winner seal; do not backdate these derivative probabilities or count them as original pre-match predictions.',
   'Offers attach only with exact same-orientation player names and estimated start. No account execution is implied.'])
 with args.output.open('x',encoding='utf8') as f:json.dump(result,f,indent=2,ensure_ascii=False,allow_nan=False)
 print(json.dumps(dict(events=len(rows),probability_rows=result['probability_rows'],families=len(result['families']),production_approved=False)))

if __name__=='__main__':main()
