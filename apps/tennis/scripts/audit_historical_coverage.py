"""Verify retrospective coverage, provenance and unchanged frozen artifacts."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
import pandas as pd
ROOT=Path('data/tennis/historical_coverage_20261018')
OLD=Path('data/tennis/historical_venues_20261018')
STAGE=Path('.local/tennis_next')
TARGET=Path('C:/Users/huye/.codex/worktrees/tennis-engine/apuesta proyec/apps/tennis')
sys.path.insert(0,str(TARGET))
from tennis_engine.historical_dataset import load_historical_registry
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
reg=load_historical_registry(ROOT/'registry.json')
report=json.loads((ROOT/'dataset_report.json').read_text())
d=pd.read_parquet(ROOT/'matches_spatial.parquet')
e=pd.read_parquet(ROOT/'eligible_spatial_cohort.parquet')
assert sha(ROOT/'registry.json')==report['registry_sha256']
assert len(d)==11240 and len(e)==5798 and d.match_id.is_unique
assert d.venue_id.notna().all() and int(d.target_coordinate_available.sum())==10510
assert d.groupby('block_id').partition.nunique().eq(1).all()
assert d.groupby('comparison_block_id').partition.nunique().eq(1).all()
assert d.historical_reconstruction.all() and not d.genuine_asof_validation.any()
assert not d.edition_id.str.startswith('2026-').any()
for col in ['rest_hours','a_rest_hours','b_rest_hours']:assert d[col].isna().all()
for side in ('a','b'):
    cols=[side+'_'+k for k in ('distance_km','delta_altitude_m','delta_timezone_hours')]
    assert np.isfinite(e[cols].to_numpy()).all()
    assert d.groupby(['block_id','player_'+side,'venue_id'])[cols].nunique(dropna=False).le(1).all().all()
    unknown=d[side+'_status'].eq('immediate_previous_edition_unlinked')
    assert d.loc[unknown,side+'_distance_km'].isna().all()
pending=json.loads((OLD/'pending_editions.json').read_text())
individual=[x for x in pending if x['venue_status']=='unlinked' and x['pending_reason']!='multivenue_or_team_event_requires_tie_level_venue']
assert len(individual)==52
linked={(x['circuit'],x['phase'],x['tourney_id']) for x in reg['links']}
assert all((x['circuit'],x['phase'],x['tourney_id']) in linked for x in individual)
original17='kempes smu santiago marrakech mallorca devonshire bastad gstaad atlanta umag jiujiang nautica bogota guadalajara prague homburg ciric'.split()
venues={x['venue_id']:x for x in reg['venues']}
assert all(venues[k].get('lat') is not None and venues[k].get('altitude_m') is not None and venues[k].get('timezone') for k in original17)
assert not reg['team_review'] and not reg['team_review_summary']['unresolved_match_locations']
assert reg['team_review_summary']['original_blocks']==233
assert len(reg['match_links'])==178
assert sum(v.get('lat') is None for v in venues.values())==88
assert all(v.get('altitude_m') is not None for v in venues.values() if v.get('lat') is not None)
for raw in report['raw_sources']:assert sha(raw['source_path'])==raw['sha256']
assert sha('data/tennis/full_20261016/canonical/matches.parquet')==report['canonical_sha256']
baseline=json.loads((ROOT/'baseline_regression/dataset_report.json').read_text())
assert baseline['n_eligible_spatial_probability_cohort']==2982
frozen=json.loads(Path('data/tennis/extension_20261017/future_protocol.json').read_text())['artifacts']
assert len(frozen)==12 and all(sha(p)==s for p,s in frozen.items())
files=['tennis_engine/historical_dataset.py','tests/test_historical_dataset.py','scripts/prepare_historical_dataset.py','scripts/build_coverage_registry.py','scripts/coverage_team_completion.py']
assert all(sha(STAGE/f)==sha(TARGET/f) for f in files)
audit=dict(schema='tennis-historical-coverage-audit-v1',original_individual_links_resolved=52,
 original_venues_georeferenced=17,team_blocks_reviewed=233,n_target_matches=len(d),n_spatial_eligible=len(e),
 n_target_coordinates=int(d.target_coordinate_available.sum()),additional_registry_entries_without_coordinates=88,
 sources_verified=len(reg['sources']),frozen_hashes_verified=12,baseline_regression_eligible=2982,
 whole_official_competition_partitions=True,unknown_antecedents_not_skipped=True,rest_imputed=False,
 genuine_asof_validation=False,metrics_computed=False,probabilities_modified=False,odds_credits_consumed=0,
 eligible_by_partition_circuit={str(k):int(v) for k,v in e.groupby(['partition','circuit']).size().items()},
 delivered_code_sha256={f:sha(TARGET/f) for f in files},
 dataset_files_sha256={f:sha(ROOT/f) for f in ['registry.json','matches_spatial.parquet','eligible_spatial_cohort.parquet','edition_catalog.json','pending_editions.json','split_manifest.json','dataset_report.json']})
(ROOT/'delivery_audit.json').write_text(json.dumps(audit,indent=2))
print(json.dumps({k:v for k,v in audit.items() if 'sha256' not in k},indent=2))
