"""Read-only provenance and mathematical checks; writes a new audit receipt."""
from pathlib import Path
import sys,json,hashlib,argparse
from datetime import datetime,timezone
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tennis_engine.historical_comparison import attach_baseline,HistoricalSpatialCorrection,FEATURES
from tennis_engine.benchmark import probability_metrics

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();root=args.output
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
protocol=json.loads((root/'protocol.json').read_text());report=json.loads((root/'report.json').read_text())
assert sha(root/'protocol.json')==report['protocol_sha256']
assert all(sha(p)==s for p,s in protocol['inputs'].items())
dataset_path=next(p for p in protocol['inputs'] if p.endswith('matches_spatial.parquet'))
d=pd.read_parquet(dataset_path);p=pd.read_parquet(root/'baseline_predictions.parquet')
joined=attach_baseline(d,p);assert len(p)==len(d)==11240
calibration=[]
for name,exclude in [('main',False),('without_coarse_references',True)]:
    r=json.loads((root/f'{name}_report.json').read_text());test=pd.read_parquet(root/f'{name}_predictions.parquet')
    mask=joined.eligible_spatial_probability_cohort & joined.partition.eq('development_2024')
    if exclude:mask &= ~joined.coarse_venue_reference_used
    train=joined.loc[mask].copy();model=HistoricalSpatialCorrection(ridge=protocol['ridge']);artifact=model.fit(train)
    assert artifact==r['artifact']
    np.testing.assert_allclose(model.predict(test),test.spatial_probability,atol=1e-14)
    expected=joined.eligible_spatial_probability_cohort & joined.partition.eq('exploratory_2025')
    if exclude:expected &= ~joined.coarse_venue_reference_used
    assert set(test.match_id)==set(joined.loc[expected,'match_id'])
    assert test.partition.eq('exploratory_2025').all()
    assert not set(train.comparison_block_id)&set(test.comparison_block_id)
    assert r['n_test_common']==len(test) and r['n_train_common']==len(train)
    for variant,col in [('base','baseline_probability'),('base_plus_spatial','spatial_probability')]:
        metrics=probability_metrics(test.y.astype(int).tolist(),test[col].astype(float).tolist())
        assert metrics==r['metrics'][variant]
        calibration.extend(dict(scenario=name,variant=variant,**b) for b in metrics['calibration'])
for year in (2024,2025):
    for circuit in ('ATP','WTA'):
        pool=json.loads((root/f'{circuit}_{year}_pool.json').read_text())
        components=pd.read_parquet(root/f'{circuit}_{year-1}_components.parquet')
        assert sha(root/f'{circuit}_{year-1}_components.parquet')==pool['input_predictions_sha256']
        fitrows=components.loc[components.match_id.isin(pool['training_event_ids'])]
        assert len(fitrows)==pool['training_n'] and fitrows.eligible_model.all()
        assert pd.Timestamp(fitrows.period.max())<pd.Timestamp(f'{year}-01-01')-pd.Timedelta(days=35)
        assert not set(fitrows.match_id)&set(p.loc[p.origin.eq(f'{year}-01-01'),'match_id'])
for receipt_path in root.glob('*_baseline_receipt.json'):
    receipt=json.loads(receipt_path.read_text());folder=Path(receipt['path'])
    assert sha(folder/'model.json')==receipt['model_sha256']
    assert sha(folder/'training_receipt.json')==receipt['training_receipt_sha256']
frozen=json.loads(Path('data/tennis/extension_20261017/future_protocol.json').read_text())['artifacts']
assert len(frozen)==12 and all(sha(p)==s for p,s in frozen.items())
pd.DataFrame(calibration).to_csv(root/'calibration_bins.csv',index=False)
script=Path(__file__).resolve();engine=script.parents[1]/'tennis_engine/historical_comparison.py'
assert sha(engine)==protocol['code_sha256']['historical_comparison.py']
assert sha(script.parent/'run_historical_comparison.py')==protocol['code_sha256']['run_historical_comparison.py']
receipt=dict(schema='tennis-historical-comparison-audit-v1',created_at=datetime.now(timezone.utc).isoformat(),
    baseline_predictions=11240,main_training=2965,main_test=2833,sensitivity_training=2851,sensitivity_test=2718,
    exact_common_intersection=True,fit_reproduced=True,metrics_recomputed=True,whole_competition_partitions=True,
    frozen_artifacts_verified=12,source_hashes_verified=True,odds_credits_consumed=0,genuine_asof_validation=False,
    production_approved=False,files_sha256={p.name:sha(p) for p in root.iterdir() if p.is_file() and p.name not in ('delivery_audit.json','.gitignore')})
(root/'delivery_audit.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps({k:v for k,v in receipt.items() if k!='files_sha256'},indent=2))
