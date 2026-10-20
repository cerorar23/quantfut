"""Exploratory fixed-contract 2026 backtest using pre-2026 trained models.

This does not use current October models to predict earlier matches, does not
select bookmaker lines, and does not infer ROI from outcomes without prices.
"""
from pathlib import Path
import argparse,json,hashlib,re,sys
from dataclasses import asdict
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from tennis_engine.model import ServeModel
from tennis_engine.scoring import Rules
from tennis_engine.benchmark import probability_metrics
from tennis_markets_v2 import MarketEngine,Contract

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def label(c,sets):
 if c.kind=='winner':return 1 if sum(a>b for a,b in sets)>sum(a<b for a,b in sets) else -1
 if c.kind=='correct_score':return 1 if (sum(a>b for a,b in sets),sum(a<b for a,b in sets))==c.score else -1
 if c.kind=='tiebreak':return 1 if any({a,b}=={6,7} for a,b in sets) else -1
 if c.set_number:
  if len(sets)<c.set_number:return 0
  ga,gb=sets[c.set_number-1]
  return ga-gb if c.kind=='set_winner' else ga+gb-c.line if c.kind=='set_games_total' else ga-gb+c.line
 if c.kind=='games_total':return sum(a+b for a,b in sets)-c.line
 if c.kind=='games_handicap':return sum(a-b for a,b in sets)+c.line
 if c.kind=='sets_total':return len(sets)-c.line
 return sum(a>b for a,b in sets)-sum(a<b for a,b in sets)+c.line

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False)
 inputs={str(args.root/'canonical/matches.parquet'):sha(args.root/'canonical/matches.parquet')};protocol=dict(schema='tennis-market-backtest-v2',fit_origin='2026-01-01',
  test_year=2026,label='exploratory_already_inspected_2026',families=10,fixed_games_total=22.5,fixed_games_handicap=-3.5,fixed_period_total=9.5,
  fixed_period_handicap=-1.5,fixed_sets_total_bo3=2.5,fixed_sets_total_bo5=3.5,fixed_sets_handicap=-1.5,
  no_price_or_line_selection=True,financial_validation=False,production_approved=False)
 with (args.output/'protocol.json').open('x',encoding='utf8') as f:json.dump(protocol,f,indent=2)
 source=pd.read_parquet(args.root/'canonical/matches.parquet').set_index('match_id',verify_integrity=True);records=[];coverage={}
 for circuit in ('ATP','WTA'):
  folder=args.root/'experiments'/(circuit+'_2026');model=ServeModel(folder/'model',uncertainty=False)
  if model.summary['cutoff']!='2026-01-01':raise ValueError('Pre-2026 model required')
  held=pd.read_parquet(folder/'heldout_predictions.parquet');excluded=Counter()
  for path in [folder/'heldout_predictions.parquet',folder/'model/model.json']:inputs[str(path)]=sha(path)
  for i,ref in enumerate(held.itertuples()):
   row=source.loc[ref.match_id]
   if row.period<'2026-01-01' or row.circuit!=circuit or not row.completed_standard:raise ValueError('Heldout match contract differs')
   if ref.a not in model.names or ref.b not in model.names:excluded['unknown_canonical_player']+=1;continue
   if any(sum(name==model.names[pid] for name in model.names.values())!=1 for pid in (ref.a,ref.b)):excluded['ambiguous_full_name']+=1;continue
   point=model.predict(ref.a,ref.b,row.surface,uncertainty=False)
   if point['unknown_effects']:excluded['unknown_player_surface_parameter']+=1;continue
   rules=Rules(int(row.best_of),deciding_tiebreak=10 if row.tourney_level=='G' else 7);engine=MarketEngine(point['p'],point['q'],rules)
   sets=[tuple(map(int,t)) for t in re.findall(r'(\d+)-(\d+)(?:\(\d+\))?',row.score)]
   if ref.a!=row.winner_id:sets=[(b,a) for a,b in sets]
   contracts=[Contract('winner','A'),Contract('tiebreak','yes'),Contract('games_total','over',22.5),Contract('games_handicap','A',-3.5),Contract('sets_total','over',2.5 if rules.best_of==3 else 3.5),Contract('sets_handicap','A',-1.5)]
   for number in (1,2):contracts.extend([Contract('set_winner','A',set_number=number),Contract('set_games_total','over',9.5,number),Contract('set_games_handicap','A',-1.5,number)])
   need=rules.best_of//2+1
   for loser in range(need):contracts.extend([Contract('correct_score','exact',score=(need,loser)),Contract('correct_score','exact',score=(loser,need))])
   for c in contracts:
    prob=engine.probabilities(c);value=label(c,sets)
    records.append(dict(match_id=ref.match_id,circuit=circuit,best_of=rules.best_of,contract=json.dumps(asdict(c),sort_keys=True),outcome='push' if value==0 else 'win' if value>0 else 'loss',probability_no_push=prob['win']/(1-prob['push']) if prob['push']<1 else None))
   if (i+1)%500==0:print(circuit,i+1,'/',len(held),flush=True)
  coverage[circuit]=dict(total=len(held),excluded=dict(excluded),evaluated=len(held)-sum(excluded.values()))
 frame=pd.DataFrame(records);frame.to_parquet(args.output/'fixed_contract_predictions.parquet',index=False);metrics=[]
 for (circuit,best_of,contract),group in frame.groupby(['circuit','best_of','contract']):
  binary=group.loc[group.outcome.ne('push') & group.probability_no_push.notna()]
  metric=probability_metrics(binary.outcome.eq('win').astype(int).tolist(),binary.probability_no_push.tolist()) if len(binary) else None
  metrics.append(dict(circuit=circuit,best_of=int(best_of),contract=json.loads(contract),total=len(group),pushes=int(group.outcome.eq('push').sum()),metric_coverage=len(binary)/len(group),metrics=metric))
 if any(sha(p)!=s for p,s in inputs.items()):raise ValueError('Backtest source changed during evaluation')
 report=dict(protocol=protocol,coverage=coverage,metrics=metrics,input_sha256=inputs,financial_validation=False,production_approved=False,
  limits=['Retrospective inputs; historical availability incomplete. 2026 was already inspected, so this is exploratory.',
   'Excludes unresolved identities and missing surface parameters; coverage reported explicitly.',
   'No bookmaker prices, returns, or prospective superiority are inferred from probability scores.'])
 with (args.output/'report.json').open('x',encoding='utf8') as f:json.dump(report,f,indent=2,allow_nan=False)
 print(json.dumps(dict(coverage=coverage,probability_rows=len(records))))

if __name__=='__main__':main()
