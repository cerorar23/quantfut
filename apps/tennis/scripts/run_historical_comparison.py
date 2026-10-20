"""Reconstruct the Markov/Elo family before adding historical spatial covariates.

Run from the main workspace. No network calls or operational model changes.
The versioned output must be new; individual completed fits can be resumed.
"""
from pathlib import Path
import sys,json,hashlib,argparse
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from scipy.special import expit
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tennis_engine.model import train,training_rows,ServeModel
from tennis_engine.evaluate import elo_ratings
from tennis_engine.scoring import Rules,match_win
from tennis_engine.research import fit_pool,pooled
from tennis_engine.historical_comparison import compare_historical

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root',type=Path,default=Path('data/tennis/full_20261016'))
parser.add_argument('--dataset',type=Path,default=Path('data/tennis/historical_coverage_20261018'))
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
write=lambda path,value:path.write_text(json.dumps(value,indent=2,allow_nan=False))
sources={str(p.resolve()):sha(p) for p in [args.root/'canonical/matches.parquet',args.dataset/'matches_spatial.parquet',args.dataset/'registry.json']}
protocol=dict(schema='tennis-retrospective-spatial-protocol-v1',inputs=sources,
 baseline='Same Markov MAP + blended-surface Elo symmetric logit pool family; reconstructed per historical origin, not current frozen coefficients',
 origins=['2023-01-01','2024-01-01','2025-01-01'],serve_training_since='2018-01-01',embargo_days=35,
 calibration='For origin Y use predictions from frozen origin Y-1, labelled before Y minus 35 days; full source editions',
 correction_training='development_2024 only',evaluation='exploratory_2025 only',ridge=1.,
 sensitivity='Independent train-only refit excluding origin/destination reference allowances above 1000m',
 pool_fit_unit='circuit',spatial_fit_unit='shared ATP/WTA coefficients',bootstrap='1000 paired competition blocks, seed20261018',
 genuine_asof_validation=False,production_approved=False,posterior_integrated=False,financial_validation=False,
 code_sha256={p.name:sha(p) for p in [Path(__file__),Path(__file__).resolve().parents[1]/'tennis_engine/historical_comparison.py']})
protocol_path=out/'protocol.json'
if protocol_path.exists():
    saved=json.loads(protocol_path.read_text());assert {k:v for k,v in saved.items() if k!='created_at'}==protocol,'Protocol changed: use a new output directory'
else:write(protocol_path,{**protocol,'created_at':datetime.now(timezone.utc).isoformat()})
if (out/'report.json').exists():raise ValueError('Completed experiment is immutable; use a new version')
canonical=pd.read_parquet(args.root/'canonical/matches.parquet')
dataset=pd.read_parquet(args.dataset/'matches_spatial.parquet')
assert dataset.match_id.is_unique and canonical.match_id.is_unique
target_ids=set(dataset.match_id)
assert not dataset.edition_id.str.startswith('2026-').any()

def base_predictions(frame,circuit,year):
    folder=out/'models'/f'{circuit}_{year}'
    existing=args.root/'experiments'/f'{circuit}_{year}'/'model'
    # Read-only reuse of already fitted 2025 origins after receipt validation.
    if year==2025 and (existing/'training_receipt.json').exists():folder=existing
    if not (folder/'model.json').exists():
        print(f'Fitting {circuit} origin {year}',flush=True)
        train(args.root,folder,circuit,f'{year}-01-01')
    receipt=json.loads((folder/'training_receipt.json').read_text())
    assert receipt['canonical_sha256']==sources[str((args.root/'canonical/matches.parquet').resolve())]
    assert receipt['cutoff']==f'{year}-01-01' and receipt['circuit']==circuit
    assert pd.Timestamp(receipt['last_source_period'])<pd.Timestamp(receipt['cutoff'])-pd.Timedelta(days=35)
    model=ServeModel(folder,uncertainty=False)
    overall,surface=elo_ratings(training_rows(args.root,circuit,f'{year}-01-01'))
    records=[]
    for i,row in enumerate(frame.sort_values('match_id').itertuples()):
        a,b=sorted((row.winner_id,row.loser_id))
        point=model.predict(a,b,row.surface,uncertainty=False)
        markov=match_win(point['p'],point['q'],Rules(int(row.best_of),deciding_tiebreak=10 if row.tourney_level=='G' else 7))
        elo=float(expit(np.log(10)*((overall[a]-overall[b])+(surface[(a,row.surface)]-surface[(b,row.surface)]))/800))
        records.append(dict(match_id=row.match_id,player_a=a,player_b=b,y=int(a==row.winner_id),period=row.period,
            circuit=circuit,eligible_model=bool(row.eligible_model),tourney_id=row.tourney_id,
            model_probability=markov,surface_elo_probability=elo,origin=f'{year}-01-01',training_latest_period=receipt['last_source_period']))
        if (i+1)%500==0:print(f'{circuit} {year}: {i+1}/{len(frame)} baseline probabilities',flush=True)
    result=pd.DataFrame(records)
    result.to_parquet(out/f'{circuit}_{year}_components.parquet',index=False)
    model_receipt=dict(path=str(folder.resolve()),model_sha256=sha(folder/'model.json'),training_receipt_sha256=sha(folder/'training_receipt.json'))
    write(out/f'{circuit}_{year}_baseline_receipt.json',model_receipt)
    return result

def calibration_frame(frame,origin):
    # Gate entire source editions, not just individual rows near the cutoff.
    upper=pd.Timestamp(origin)-pd.Timedelta(days=35)
    last=frame.groupby('tourney_id').period.transform('max')
    selected=frame.loc[frame.eligible_model & pd.to_datetime(last).lt(upper)].copy()
    if len(selected)<100:raise ValueError('Insufficient historical calibration')
    return selected

all_predictions=[]
for circuit in ('ATP','WTA'):
    subset=canonical.loc[canonical.circuit.eq(circuit) & canonical.source_group.eq('tour')]
    c2023=subset.loc[subset.tourney_id.str.startswith('2023-') & subset.completed_standard].copy()
    c2024=subset.loc[subset.match_id.isin(target_ids) & subset.tourney_id.str.startswith('2024-')].copy()
    c2025=subset.loc[subset.match_id.isin(target_ids) & subset.tourney_id.str.startswith('2025-')].copy()
    previous=base_predictions(c2023,circuit,2023)
    for year,frame in ((2024,c2024),(2025,c2025)):
        calibration=calibration_frame(previous,f'{year}-01-01')
        params=fit_pool(calibration);params.update(circuit=circuit,origin=f'{year}-01-01',
            input_predictions_sha256=sha(out/f'{circuit}_{year-1}_components.parquet'),
            training_event_ids=calibration.match_id.tolist())
        write(out/f'{circuit}_{year}_pool.json',params)
        current=base_predictions(frame,circuit,year)
        current['baseline_probability']=pooled(current,params)
        current['pool_latest_period']=params['last_period']
        all_predictions.append(current[['match_id','player_a','player_b','y','baseline_probability','origin','training_latest_period','pool_latest_period']])
        previous=current
predictions=pd.concat(all_predictions,ignore_index=True)
assert len(predictions)==len(dataset)
predictions.to_parquet(out/'baseline_predictions.parquet',index=False)
reports={}
for name,exclude in [('main',False),('without_coarse_references',True)]:
    scored,report=compare_historical(dataset,predictions,exclude_coarse=exclude,ridge=1.)
    scored.to_parquet(out/f'{name}_predictions.parquet',index=False)
    write(out/f'{name}_report.json',report);reports[name]=report
assert all(sha(p)==value for p,value in sources.items())
frozen=json.loads(Path('data/tennis/extension_20261017/future_protocol.json').read_text())['artifacts']
assert len(frozen)==12 and all(sha(p)==value for p,value in frozen.items())
summary=dict(created_at=datetime.now(timezone.utc).isoformat(),status='evaluated',label='exploratory_retrospective_2025',
    protocol_sha256=sha(protocol_path),reports={name:{k:v for k,v in r.items() if k!='artifact'} for name,r in reports.items()},
    frozen_artifacts_unchanged=12,odds_credits_consumed=0,production_approved=False,financial_validation=False)
write(out/'report.json',summary)
print(json.dumps({name:{k:r[k] for k in ['n_train_common','n_test_common','coverage','metrics','paired']} for name,r in reports.items()},indent=2),flush=True)
