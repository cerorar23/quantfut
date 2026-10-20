"""Local, source-pinned earlier-round workload comparison; no daily time imputation."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,hashlib,sys,sqlite3
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tennis_engine.draw_load import extract_draw_load,compare_draw_load
from tennis_engine.recent_load import api_tennis_history

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=False)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
write=lambda name,value:(out/name).write_text(json.dumps(value,indent=2,allow_nan=False))
canonical_path=Path('data/tennis/full_20261016/canonical/matches.parquet')
dataset_path=Path('data/tennis/historical_coverage_20261018/matches_spatial.parquet')
base_root=Path('data/tennis/historical_comparison_20261018')
baseline_path=base_root/'baseline_predictions.parquet'
source_protocol=json.loads((base_root/'protocol.json').read_text())
assert all(sha(p)==s for p,s in source_protocol['inputs'].items())
inputs={str(p.resolve()):sha(p) for p in [canonical_path,dataset_path,baseline_path,base_root/'protocol.json']}
code=Path(__file__).resolve().parents[1]/'tennis_engine/draw_load.py'
write('protocol.json',dict(schema='tennis-draw-load-protocol-v1',created_at=datetime.now(timezone.utc).isoformat(),inputs=inputs,
    code_sha256={code.name:sha(code),Path(__file__).name:sha(__file__)},
    training='development_2024',evaluation='exploratory_2025',ridge=1.,minimum_training_rows=100,
    variants=['base','base_plus_coverage','base_plus_coverage_plus_load'],
    primary='Both players have observed play in earlier knockout rounds of the same draw; completed standard targets',
    sensitivity='Refit with complete counters among the observed prior records for both players',
    bootstrap='1000 paired competition blocks, seed20261018',actual_day_windows=False,
    genuine_asof_validation=False,test_used_for_tuning=False,production_approved=False))
canonical=pd.read_parquet(canonical_path);dataset=pd.read_parquet(dataset_path);baseline=pd.read_parquet(baseline_path)
# Same-draw histories use all outcomes/counters, not only model-eligible rows.
keys=set(zip(dataset.circuit,dataset.edition_id))
history=canonical.loc[[group=='tour' and (circuit,edition) in keys for group,circuit,edition in zip(canonical.source_group,canonical.circuit,canonical.tourney_id)]].copy()
assert not history.tourney_id.str.startswith('2026-').any()
load,extraction=extract_draw_load(history,dataset)
load.to_parquet(out/'draw_load_features.parquet',index=False);write('extraction_report.json',extraction)
reports={};calibration=[]
for name,complete in [('main',False),('complete_observed_counters',True)]:
    predictions,report=compare_draw_load(dataset,baseline,load,complete_counters_only=complete)
    predictions.to_parquet(out/f'{name}_predictions.parquet',index=False);write(f'{name}_report.json',report)
    reports[name]={k:v for k,v in report.items() if k!='artifacts'}
    for variant,metrics in report['metrics'].items():
        calibration.extend(dict(scenario=name,variant=variant,**row) for row in metrics['calibration'])
pd.DataFrame(calibration).to_csv(out/'calibration_bins.csv',index=False)

# Audit archived real observation bounds without connecting or writing to API-Tennis.
db_path=Path('data/tennis/state_capture_20261017/states.sqlite').resolve()
db=sqlite3.connect(db_path.as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
latest={r['event_id']:dict(r) for r in db.execute('SELECT event_id,receipt_id,state,received_at FROM observations ORDER BY received_at,receipt_id')}
observations=[];receipt_sources=[]
for r in db.execute('SELECT * FROM receipts ORDER BY received_at,id'):
    rows=api_tennis_history(Path(r['source_path']),r['received_at'],r['sha256'])
    observations.extend(x for x in rows if x.event_id in latest and latest[x.event_id]['receipt_id']==r['id'])
    receipt_sources.append(dict(source_path=r['source_path'],sha256=r['sha256'],received_at=r['received_at']))
db.close()
daily=dict(status='insufficient_verified_completion_bounds',latest_terminal_singles=len(observations),
    with_finite_completion_lower_bound=sum(x.ended_after[:4]!='0001' for x in observations),
    retained_unknown_lower_bounds=sum(x.ended_after[:4]=='0001' for x in observations),
    archive_sources=receipt_sources,scheduled_dates_promoted_to_actual=False,windows_3d_7d_ready=False,
    note='Receipt of a terminal state is an upper bound only; a scheduled date does not verify actual completion day')
assert daily['with_finite_completion_lower_bound']==0
write('strict_daily_feasibility.json',daily)
frozen=json.loads(Path('data/tennis/extension_20261017/future_protocol.json').read_text())['artifacts']
assert len(frozen)==12 and all(sha(p)==s for p,s in frozen.items())
assert all(sha(p)==s for p,s in inputs.items())
write('report.json',dict(created_at=datetime.now(timezone.utc).isoformat(),reports=reports,extraction=extraction,
    strict_daily_feasibility=daily,frozen_artifacts_unchanged=12,odds_credits_consumed=0,new_sports_provider_calls=0,
    production_approved=False,financial_validation=False))
print(json.dumps({name:dict(train=r['n_train_common'],test=r['n_test_common'],metrics={v:{k:m[k] for k in ['log_loss','brier','ece']} for v,m in r['metrics'].items()},paired=r['paired']) for name,r in reports.items()},indent=2),flush=True)
