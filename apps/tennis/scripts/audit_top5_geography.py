"""Audit the five-venue extension and report coverage without refitting models."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,hashlib
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tennis_engine.historical_dataset import load_historical_registry

root=Path('data/tennis/historical_geography_top5_20261018')
parent=Path('data/tennis/historical_coverage_20261018')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
reg=load_historical_registry(root/'registry.json');old=load_historical_registry(parent/'registry.json')
assert reg['parent_registry_sha256']==sha(parent/'registry.json')
assert reg['links']==old['links'] and reg['match_links']==old['match_links']
before={v['venue_id']:v for v in old['venues']};after={v['venue_id']:v for v in reg['venues']}
expected={'huahin','merida','seoul','zayed','martin_carpena'}
assert {k for k in after if after[k]!=before[k]}==expected
for k in expected:
    assert before[k]['lat'] is None and after[k]['lat'] is not None
    assert after[k]['altitude_m'] is not None and after[k]['timezone']==before[k]['timezone']
assert after['merida']['coordinate_precision_m']==1800 and after['merida']['coordinate_feature']['complex_reference']
assert len(reg['geography_review'])==5
for review in reg['geography_review']:
    if review['corroboration_method']=='coordinate_comparison':
        assert review['corroborating_distance_m']<review['precision_m']
    else:assert review['venue_id']=='zayed' and review['corroborating_point'] is None
sources={s['source_id']:s for s in reg['sources']}
assert all(sources[s['source_id']]==s for s in old['sources'])
old_d=pd.read_parquet(parent/'matches_spatial.parquet').set_index('match_id',verify_integrity=True)
new_d=pd.read_parquet(root/'matches_spatial.parquet').set_index('match_id',verify_integrity=True)
assert set(old_d.index)==set(new_d.index) and len(new_d)==11240
cols=['player_a','player_b','y','block_id','comparison_block_id','partition','venue_id','score','completed_standard']
pd.testing.assert_frame_equal(old_d[cols].sort_index(),new_d[cols].sort_index())
assert old_d.target_coordinate_available.le(new_d.target_coordinate_available).all()
new_destinations=new_d.loc[new_d.target_coordinate_available & ~old_d.target_coordinate_available]
assert len(new_destinations)==264 and set(new_destinations.venue_id)==expected
assert new_d.groupby('comparison_block_id').partition.nunique().eq(1).all()
assert new_d.rest_hours.isna().all() and new_d.a_rest_hours.isna().all() and new_d.b_rest_hours.isna().all()
old_ids=set(old_d.index[old_d.eligible_spatial_probability_cohort]);new_ids=set(new_d.index[new_d.eligible_spatial_probability_cohort])
assert old_ids<=new_ids and len(new_ids)==6244 and len(new_ids-old_ids)==446
features=[s+'_'+c for s in ('a','b') for c in ['distance_km','delta_altitude_m','delta_timezone_hours']]
pd.testing.assert_frame_equal(old_d.loc[sorted(old_ids),features],new_d.loc[sorted(old_ids),features])
assert np.isfinite(new_d.loc[sorted(new_ids),features].to_numpy()).all()
affected=new_d.venue_id.eq('merida') & new_d.eligible_spatial_probability_cohort
assert new_d.loc[affected,'coarse_venue_reference_used'].all()
assert (new_d.eligible_spatial_probability_cohort & ~new_d.coarse_venue_reference_used).sum()==5943
report=json.loads((root/'dataset_report.json').read_text())
assert sha(root/'registry.json')==report['registry_sha256']
assert sha('data/tennis/full_20261016/canonical/matches.parquet')==report['canonical_sha256']
assert all(sha(s['source_path'])==s['sha256'] for s in report['raw_sources'])
# The earlier datasets and experiments remain source-pinned, not overwritten.
for folder,field in [(parent,'dataset_files_sha256'),(Path('data/tennis/historical_comparison_20261018'),'files_sha256'),
                     (Path('data/tennis/draw_load_20261018_v2'),'files_sha256')]:
    saved=json.loads((folder/'delivery_audit.json').read_text())[field]
    assert all(sha(folder/name)==digest for name,digest in saved.items())
frozen=json.loads(Path('data/tennis/extension_20261017/future_protocol.json').read_text())['artifacts']
assert len(frozen)==12 and all(sha(p)==digest for p,digest in frozen.items())
remaining=[];counts=new_d.loc[~new_d.target_coordinate_available].groupby('venue_id').size().to_dict()
for v in reg['venues']:
    if v.get('lat') is None:remaining.append(dict(venue_id=v['venue_id'],name=v['name'],city=v.get('city'),country=v.get('country'),
        affected_target_matches=int(counts.get(v['venue_id'],0)),status='coordinates_unverified'))
remaining.sort(key=lambda r:(-r['affected_target_matches'],r['venue_id']))
assert len(remaining)==83 and sum(r['affected_target_matches'] for r in remaining)==466
(root/'geography_priority_queue.json').write_text(json.dumps(remaining,indent=2))
gained=new_d.loc[sorted(new_ids-old_ids)].copy()
gained.reset_index().to_parquet(root/'newly_eligible_matches.parquet',index=False)
summary=dict(schema='tennis-top5-geography-coverage-audit-v1',created_at=datetime.now(timezone.utc).isoformat(),
    before=dict(target_coordinates=10510,spatial_eligible=5798,without_coarse=5569,unverified_entries=88),
    after=dict(target_coordinates=10774,spatial_eligible=6244,without_coarse=5943,unverified_entries=83),
    recovered_target_matches=264,new_spatial_eligible=446,
    recovered_destinations_by_venue={str(k):int(v) for k,v in new_destinations.groupby('venue_id').size().items()},
    eligible_by_partition_circuit={str(k):int(v) for k,v in new_d.loc[sorted(new_ids)].groupby(['partition','circuit']).size().items()},
    newly_eligible_by_partition_circuit={str(k):int(v) for k,v in gained.groupby(['partition','circuit']).size().items()},
    registry_entries=240,georeferenced_entries=157,sources_verified=len(reg['sources']),
    historical_bindings_unchanged=True,old_eligible_features_unchanged=True,older_datasets_and_experiments_unchanged=True,
    frozen_artifacts_verified=12,probabilities_modified=False,metrics_recomputed=False,rest_imputed=False,
    genuine_asof_validation=False,financial_validation=False,odds_credits_consumed=0,sports_provider_requests=0,
    public_elevation_requests=1,
    delivered_builder_sha256=sha(Path(__file__).parent/'build_top5_geography.py'),
    files_sha256={p.name:sha(p) for p in root.iterdir() if p.is_file() and p.name not in ('delivery_audit.json','.gitignore')})
(root/'delivery_audit.json').write_text(json.dumps(summary,indent=2))
print(json.dumps({k:v for k,v in summary.items() if k!='files_sha256'},indent=2))
