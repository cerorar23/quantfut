"""Reproducible local dataset preparation, no remote requests or model fitting."""
import sys,json,hashlib,argparse
from pathlib import Path
from datetime import datetime,timezone
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tennis_engine.historical_dataset import load_historical_registry,prepare_historical_dataset

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--registry',type=Path,required=True)
parser.add_argument('--canonical',type=Path,required=True)
parser.add_argument('--raw-root',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();root=args.output;root.mkdir(parents=True,exist_ok=True)
registry=load_historical_registry(args.registry)
canonical=args.canonical
frame=pd.read_parquet(canonical)
frame=frame.loc[frame.period.between('2023-01-01','2025-12-31') & ~frame.tourney_id.str.startswith('2026-')].copy()
# Preserve exact canonical IDs. Source row points to the original CSV row, not a name fuzzy match.
rawroot=args.raw_root
names={};raw_sources=[]
for filename,group in frame.groupby('source_file',sort=False):
    f=rawroot/filename
    if not f.exists():f=rawroot/Path(filename).name
    if not f.exists():continue
    raw_sources.append({'source_path':str(f.resolve()),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
    raw=pd.read_csv(f,dtype=str)
    for r in group.itertuples(index=False):
        original=raw.iloc[int(r.source_row)-2]
        assert str(original.tourney_id)==str(r.tourney_id),(filename,r.source_row)
        names[r.match_id]=str(original.tourney_name)
frame['tourney_name']=frame.match_id.map(names)
data,report=prepare_historical_dataset(frame,registry)
data.to_parquet(root/'matches_spatial.parquet',index=False)
data.loc[data.eligible_spatial_probability_cohort].to_parquet(root/'eligible_spatial_cohort.parquet',index=False)
catalog=report.pop('edition_catalog');pd.DataFrame(catalog).to_json(root/'edition_catalog.json',orient='records',indent=2)
report.update(created_at=datetime.now(timezone.utc).isoformat(),registry_sha256=hashlib.sha256(args.registry.read_bytes()).hexdigest(),
              canonical_sha256=hashlib.sha256(canonical.read_bytes()).hexdigest(),
              n_source_names_joined=len(names),n_registry_links=len(registry['links']),raw_sources=raw_sources,
              coverage_spatial_eligible=report['n_eligible_spatial_probability_cohort']/report['n_target_matches'],
              timezone_note='Signed offset destination-minus-origin at identical UTC probes; ambiguous DST retained as range, not jet lag severity',
              limitations=['Last observed tournament, not actual trip or location','No complete doubles tracking','No exact exit/debut times','2025 exploratory, no model selection claim','No ROI without contemporaneous executable odds','2023 history retained but venues not projected backward'])
(root/'dataset_report.json').write_text(json.dumps(report,indent=2))
# Exact IDs per partition, including full editions and downstream monthly blocks.
split={part:{'match_ids':g.match_id.tolist(),'block_ids':sorted(g.block_id.unique().tolist()),'comparison_block_ids':sorted(g.comparison_block_id.unique().tolist())}
       for part,g in data.groupby('partition',sort=True)}
(root/'split_manifest.json').write_text(json.dumps({'schema':'tennis-historical-whole-edition-splits-v1','partitions':split,
    'indivisible_block_column':'comparison_block_id',
    'selection_status':'2025 exploratory; neither partition is a new untouched holdout',
    'common_prediction_intersection_not_yet_computed':True},indent=2))
pending=[{**x,'pending_reason':'some_match_venue_identities_missing' if x['n_matches_with_venue_identity']<x['n'] else 'physical_venue_coordinates_unverified'}
         for x in catalog if x['n_matches_with_coordinates']<x['n']]
(root/'pending_editions.json').write_text(json.dumps(pending,indent=2))
print(json.dumps(report,indent=2))
