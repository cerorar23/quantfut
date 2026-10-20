"""Replay a real archived event for connector verification, never a new pick."""
from pathlib import Path
import argparse,json,hashlib,sys
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tennis_engine.model import ServeModel
from tennis_engine.scoring import Rules
from tennis_engine.identities import normalized
from tennis_engine.operations import now
from tennis_markets_v2 import MarketEngine
from tennis_markets_v2.offers import price_offers,API_KEYS

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('receipt','model','output'):p.add_argument('--'+name,type=Path,required=True)
 args=p.parse_args();receipt=json.loads(args.receipt.read_text());source=args.receipt.parent/'response.json';raw=source.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=receipt['sha256']:raise ValueError('Original quote hash changed')
 event=json.loads(raw);model=ServeModel(args.model,uncertainty=False);ids=[]
 for field in ('home_team','away_team'):
  matches=[pid for pid,name in model.names.items() if normalized(name)==normalized(event[field])]
  if len(matches)!=1:raise ValueError('Canonical identity ambiguous')
  ids.append(matches[0])
 point=model.predict(*ids,'Hard',uncertainty=False)
 if point['unknown_effects']:raise ValueError('Missing model parameter')
 engine=MarketEngine(point['p'],point['q'],Rules(3));rows=price_offers(event,engine,receipt['received_at'],now())
 report=dict(schema='tennis-archived-markets-replay-v2',replayed_at=now(),prospective_forecast=False,
  event=dict(id=event['id'],players=[event['home_team'],event['away_team']],commence_time=event['commence_time']),
  source_path=str(source.resolve()),source_sha256=receipt['sha256'],receipt_path=str(args.receipt.resolve()),
  receipt_sha256=hashlib.sha256(args.receipt.read_bytes()).hexdigest(),model_sha256=hashlib.sha256((args.model/'model.json').read_bytes()).hexdigest(),
  original_quote_received_at=receipt['received_at'],observed_supported_keys=sorted({r['provider_market'] for r in rows if r['provider_market'] in API_KEYS}),
  rows=rows,statuses=dict(Counter(r['status'] for r in rows)),fresh_quotes=sum(r['quote_fresh'] for r in rows),
  actual_wagers_placed=0,financial_validation=False,production_approved=False,
  limit='Historical connector replay; derived now, no source time or probability backdated; not current executable odds.')
 with args.output.open('x',encoding='utf8') as f:json.dump(report,f,indent=2,ensure_ascii=False,allow_nan=False)
 print(json.dumps(dict(rows=len(rows),keys=report['observed_supported_keys'],statuses=report['statuses'],fresh_quotes=report['fresh_quotes'])))

if __name__=='__main__':main()
