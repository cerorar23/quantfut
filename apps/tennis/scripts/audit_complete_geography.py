"""Integrity and temporal audit of the complete historical geographic review."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,sys,argparse
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tennis_engine.historical_dataset import load_historical_registry
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--verify-existing',action='store_true',help='Verify archived results without writing any artifact')
args=parser.parse_args()
root=Path('data/tennis/historical_geography_complete_20261018')
parent=Path('data/tennis/historical_geography_batch3_20261018')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
reg=load_historical_registry(root/'registry.json');old=load_historical_registry(parent/'registry.json')
assert reg['parent_registry_sha256']==sha(parent/'registry.json')
assert reg['links']==old['links'] and reg['match_links']==old['match_links']
reviews=json.loads((root/'reviewed_locations.json').read_text(encoding='utf8'))
expected={v['venue_id'] for v in reviews};resolved={v['venue_id'] for v in reviews if v.get('method')!='unresolved_historical_campus'}
assert len(expected)==73 and len(resolved)==72
before={v['venue_id']:v for v in old['venues']};after={v['venue_id']:v for v in reg['venues']}
assert {k for k in after if after[k]!=before[k]}==expected
for key in resolved:
 assert before[key]['lat'] is None and after[key]['lat'] is not None
 assert after[key]['altitude_m'] is not None and after[key]['timezone'] is not None
assert after['palm_hills']['lat'] is None
assert len(after['palm_hills']['unresolved_candidate_venues'])==2
assert after['palm_hills']['coordinate_status']=='reviewed_historical_campus_ambiguous'
sources={s['source_id']:s for s in reg['sources']}
assert all(sources[s['source_id']]==s for s in old['sources'])
models=0
for f in Path('data/tennis/historical_comparison_20261018').glob('*_baseline_receipt.json'):
 r=json.loads(f.read_text());p=Path(r['path'])
 assert sha(p/'model.json')==r['model_sha256'] and sha(p/'training_receipt.json')==r['training_receipt_sha256'];models+=1
assert models==6
old_d=pd.read_parquet(parent/'matches_spatial.parquet').set_index('match_id',verify_integrity=True)
new_d=pd.read_parquet(root/'matches_spatial.parquet').set_index('match_id',verify_integrity=True)
assert set(old_d.index)==set(new_d.index) and len(new_d)==11240
cols=['player_a','player_b','y','block_id','comparison_block_id','partition','venue_id','score','completed_standard']
pd.testing.assert_frame_equal(old_d[cols].sort_index(),new_d[cols].sort_index())
assert old_d.target_coordinate_available.le(new_d.target_coordinate_available).all()
gain=new_d.loc[new_d.target_coordinate_available & ~old_d.target_coordinate_available]
assert len(gain)==283 and set(gain.venue_id)==resolved
assert new_d.groupby('comparison_block_id').partition.nunique().eq(1).all()
assert new_d.rest_hours.isna().all() and new_d.a_rest_hours.isna().all() and new_d.b_rest_hours.isna().all()
old_ids=set(old_d.index[old_d.eligible_spatial_probability_cohort]);new_ids=set(new_d.index[new_d.eligible_spatial_probability_cohort])
assert old_ids<=new_ids and len(new_ids)==6568 and len(new_ids-old_ids)==126
features=[s+'_'+c for s in ('a','b') for c in ['distance_km','delta_altitude_m','delta_timezone_hours']]
pd.testing.assert_frame_equal(old_d.loc[sorted(old_ids),features],new_d.loc[sorted(old_ids),features])
assert np.isfinite(new_d.loc[sorted(new_ids),features].to_numpy()).all()
assert (new_d.eligible_spatial_probability_cohort & ~new_d.coarse_venue_reference_used).sum()==6250
assert new_d.loc[~new_d.target_coordinate_available,'venue_id'].eq('palm_hills').all()
report=json.loads((root/'dataset_report.json').read_text())
assert sha(root/'registry.json')==report['registry_sha256']
assert sha('data/tennis/full_20261016/canonical/matches.parquet')==report['canonical_sha256']
assert all(sha(s['source_path'])==s['sha256'] for s in report['raw_sources'])
preserved=[]
for folder,field in [(parent,'files_sha256'),(parent/'comparison','files_sha256'),(Path('data/tennis/historical_geography_batch2_20261018'),'files_sha256'),(Path('data/tennis/historical_geography_batch2_20261018/comparison'),'files_sha256'),(Path('data/tennis/historical_geography_top5_20261018'),'files_sha256'),(Path('data/tennis/historical_coverage_20261018'),'dataset_files_sha256'),(Path('data/tennis/historical_comparison_20261018'),'files_sha256'),(Path('data/tennis/draw_load_20261018_v2'),'files_sha256')]:
 saved=json.loads((folder/'delivery_audit.json').read_text())[field]
 assert all(sha(folder/name)==digest for name,digest in saved.items()),folder
 preserved.append(str(folder))
frozen=json.loads(Path('data/tennis/extension_20261017/future_protocol.json').read_text())['artifacts']
assert len(frozen)==12 and all(sha(p)==digest for p,digest in frozen.items())
remaining=[dict(venue_id='palm_hills',name=after['palm_hills']['name'],city='Cairo',country='Egypt',affected_target_matches=3,status='reviewed_historical_campus_ambiguous',note=after['palm_hills']['coordinate_reference_note'])]
if not args.verify_existing:
 (root/'geography_priority_queue.json').write_text(json.dumps(remaining,indent=2),encoding='utf8')
 new_d.loc[sorted(new_ids-old_ids)].reset_index().to_parquet(root/'newly_eligible_matches.parquet',index=False)
summary=dict(schema='tennis-complete-geography-audit-v1',created_at=datetime.now(timezone.utc).isoformat(),
 before=dict(target_coordinates=int(old_d.target_coordinate_available.sum()),spatial_eligible=len(old_ids),unverified_entries=73),
 after=dict(target_coordinates=int(new_d.target_coordinate_available.sum()),spatial_eligible=len(new_ids),without_coarse=6250,unresolved_entries=1),
 reviewed_entries=73,resolved_entries=72,recovered_target_matches=len(gain),new_spatial_eligible=len(new_ids-old_ids),
 recovered_destinations_by_venue={str(k):int(v) for k,v in gain.groupby('venue_id').size().items()},
 eligible_by_partition_circuit={str(k):int(v) for k,v in new_d.loc[sorted(new_ids)].groupby(['partition','circuit']).size().items()},
 registry_entries=len(after),georeferenced_entries=sum(v.get('lat') is not None for v in after.values()),sources_verified=len(sources),
 historical_bindings_unchanged=True,old_eligible_features_unchanged=True,older_datasets_and_experiments_unchanged=preserved,
 frozen_artifacts_verified=12,cached_baseline_models_verified=models,production_probabilities_modified=False,
 experimental_probabilities_recomputed=True,metrics_recomputed=True,rest_imputed=False,genuine_asof_validation=False,
 financial_validation=False,odds_credits_consumed=0,sports_provider_requests=0,public_elevation_requests=1,
 builder_sha256=sha(Path(__file__).parent/'build_complete_geography.py'),
 files_sha256={p.name:sha(p) for p in root.iterdir() if p.is_file() and p.name not in ('delivery_audit.json','.gitignore')})
comparison=json.loads((root/'comparison/delivery_audit.json').read_text())
assert all(sha(root/'comparison'/n)==v for n,v in comparison['files_sha256'].items())
summary['comparison_files_sha256']=comparison['files_sha256']
if args.verify_existing:
 saved=json.loads((root/'delivery_audit.json').read_text())
 assert all(sha(root/n)==s for n,s in saved['files_sha256'].items())
 for field in ['before','after','reviewed_entries','resolved_entries','recovered_target_matches','new_spatial_eligible','builder_sha256']:
  assert saved[field]==summary[field],field
else:
 (root/'delivery_audit.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in summary.items() if k not in ['files_sha256','comparison_files_sha256','recovered_destinations_by_venue']},indent=2))
