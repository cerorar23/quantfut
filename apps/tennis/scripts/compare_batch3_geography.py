"""Repeat the frozen retrospective spatial protocol using cached base predictions.

No new baseline fits, API calls, hyperparameter searches or model activation.
Report both expanded coverage and the exact original 2025 evaluation cohort.
"""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,sys
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tennis_engine.historical_comparison import compare_historical,paired_interval,FEATURES,HistoricalSpatialCorrection,attach_baseline
from tennis_engine.benchmark import probability_metrics

root=Path('data/tennis/historical_geography_batch3_20261018')
out=root/'comparison';out.mkdir(exist_ok=True)
old=Path('data/tennis/historical_comparison_20261018')
parent=Path('data/tennis/historical_geography_batch2_20261018/comparison')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
write=lambda p,v:p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf8')
assert not (out/'protocol.json').exists(),'Immutable experiment already exists'
inputs=[root/'matches_spatial.parquet',root/'registry.json',old/'baseline_predictions.parquet',old/'main_predictions.parquet',old/'protocol.json']
inputs.extend([parent/'main_predictions.parquet',parent/'main_report.json'])
code=Path(__file__).resolve().parents[1]/'tennis_engine/historical_comparison.py'
protocol=dict(schema='tennis-fixed-spatial-repeat-v1',created_at=datetime.now(timezone.utc).isoformat(),
    inputs={str(p.resolve()):sha(p) for p in inputs},code_sha256={str(code.resolve()):sha(code),str(Path(__file__).resolve()):sha(__file__)},
    ridge=1.,training_partition='development_2024',evaluation_partition='exploratory_2025',
    baseline_policy='Read-only reuse of 11240 predictions from archived model receipts; existing 35-day embargo unchanged',
    features=list(FEATURES),bootstrap_draws=1000,bootstrap_seed=20261018,
    scenarios=['main','without_coarse_references'],
    common_historical_cohort='Exact IDs of the original published main_predictions.parquet',
    parent_common_cohort='Exact 3108 IDs evaluated in batch2, with unchanged features and baseline',
    all_scenarios_reported=True,hyperparameter_search=False,production_approved=False,
    test_used_for_tuning=False,financial_validation=False,genuine_asof_validation=False,
    prospective_requirement='New untouched future evaluation after training; existing frozen holdout not repurposed')
# Persist the complete protocol before fitting or scoring.
write(out/'protocol.json',protocol)
dataset=pd.read_parquet(root/'matches_spatial.parquet')
base=pd.read_parquet(old/'baseline_predictions.parquet')
assert len(base)==11240
reports={};calibration=[]
for name,exclude in [('main',False),('without_coarse_references',True)]:
    test,report=compare_historical(dataset,base,exclude_coarse=exclude,ridge=protocol['ridge'])
    test.to_parquet(out/f'{name}_predictions.parquet',index=False)
    write(out/f'{name}_report.json',report)
    # Independent reproduction of coefficients, predictions and metric records.
    joined=attach_baseline(dataset,base)
    mask=joined.eligible_spatial_probability_cohort & joined.partition.eq('development_2024')
    if exclude:mask &= ~joined.coarse_venue_reference_used
    fitted=HistoricalSpatialCorrection(ridge=1.)
    assert fitted.fit(joined.loc[mask])==report['artifact']
    np.testing.assert_allclose(fitted.predict(test),test.spatial_probability,rtol=0,atol=1e-14)
    assert not set(joined.loc[mask,'comparison_block_id'])&set(test.comparison_block_id)
    for variant,col in [('base','baseline_probability'),('base_plus_spatial','spatial_probability')]:
        metrics=probability_metrics(test.y.astype(int).tolist(),test[col].astype(float).tolist())
        assert metrics==report['metrics'][variant]
        calibration.extend(dict(scenario=name,variant=variant,**b) for b in metrics['calibration'])
    if name=='main':
        previous=pd.read_parquet(old/'main_predictions.parquet').set_index('match_id',verify_integrity=True)
        current=test.set_index('match_id',verify_integrity=True)
        assert set(previous.index)<=set(current.index)
        common=current.loc[sorted(previous.index)].copy()
        for col in ['y','player_a','player_b','comparison_block_id',*FEATURES,'baseline_probability']:
            pd.testing.assert_series_equal(previous.loc[common.index,col],common[col],check_names=True)
        common['previous_spatial_probability']=previous.loc[common.index,'spatial_probability']
        common.to_parquet(out/'original_common_cohort.parquet')
        summary=dict(n=len(common),metrics={k:probability_metrics(common.y.astype(int).tolist(),common[c].astype(float).tolist())
            for k,c in [('base','baseline_probability'),('previous_spatial','previous_spatial_probability'),('expanded_training_spatial','spatial_probability')]},
            expanded_vs_base=paired_interval(common),
            expanded_vs_previous=paired_interval(common.assign(baseline_probability=common.previous_spatial_probability)),
            explanation='Identical original evaluation IDs, labels, baseline and features; only the development training cohort expands. Neither candidate selected on 2025.')
        write(out/'original_common_cohort_report.json',summary)
        previous_parent=pd.read_parquet(parent/'main_predictions.parquet').set_index('match_id',verify_integrity=True)
        assert set(previous_parent.index)<=set(current.index)
        parent_common=current.loc[sorted(previous_parent.index)].copy()
        for col in ['y','player_a','player_b','comparison_block_id',*FEATURES,'baseline_probability']:
            pd.testing.assert_series_equal(previous_parent.loc[parent_common.index,col],parent_common[col])
        parent_common['parent_spatial_probability']=previous_parent.loc[parent_common.index,'spatial_probability']
        parent_common.to_parquet(out/'parent_common_cohort.parquet')
        parent_summary=dict(n=len(parent_common),metrics={k:probability_metrics(parent_common.y.astype(int).tolist(),parent_common[c].astype(float).tolist())
            for k,c in [('base','baseline_probability'),('batch2_spatial','parent_spatial_probability'),('batch3_spatial','spatial_probability')]},
            batch3_vs_batch2=paired_interval(parent_common.assign(baseline_probability=parent_common.parent_spatial_probability)),
            explanation='Exact parent evaluation IDs, labels, baseline and features; no selection on 2025.')
        write(out/'parent_common_cohort_report.json',parent_summary)
    reports[name]={k:v for k,v in report.items() if k!='artifact'}
pd.DataFrame(calibration).to_csv(out/'calibration_bins.csv',index=False)
assert all(sha(p)==digest for p,digest in {**protocol['inputs'],**protocol['code_sha256']}.items())
frozen=json.loads(Path('data/tennis/extension_20261017/future_protocol.json').read_text())['artifacts']
assert len(frozen)==12 and all(sha(p)==v for p,v in frozen.items())
report=dict(created_at=datetime.now(timezone.utc).isoformat(),protocol_sha256=sha(out/'protocol.json'),
    reports=reports,original_common_cohort=summary,parent_common_cohort=parent_summary,production_approved=False,financial_validation=False,
    frozen_artifacts_verified=12,baseline_refitted=False,odds_credits_consumed=0,sports_provider_requests=0)
write(out/'report.json',report)
write(out/'delivery_audit.json',dict(created_at=datetime.now(timezone.utc).isoformat(),
    fits_reproduced=True,metrics_recomputed=True,source_hashes_verified=True,exact_common_intersection=True,
    frozen_artifacts_verified=12,files_sha256={p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name!='delivery_audit.json'}))
print(json.dumps({k:{x:v[x] for x in ['n_train_common','n_test_common','coverage','metrics','paired']} for k,v in reports.items()},indent=2))
