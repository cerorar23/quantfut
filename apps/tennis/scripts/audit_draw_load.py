"""Reproduce the extracted prior-round counters and training-only corrections."""
from pathlib import Path
import sys,json,hashlib,argparse
from datetime import datetime,timezone
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tennis_engine.draw_load import (extract_draw_load,DrawLoadCorrection,ROUND_ORDER,CONTROL_FEATURES,LOAD_FEATURES)
from tennis_engine.historical_comparison import attach_baseline
from tennis_engine.benchmark import probability_metrics

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();root=args.output
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
protocol=json.loads((root/'protocol.json').read_text());summary=json.loads((root/'report.json').read_text())
assert all(sha(p)==value for p,value in protocol['inputs'].items())
canonical_path=next(p for p in protocol['inputs'] if p.endswith('canonical/matches.parquet') or p.endswith('canonical\\matches.parquet'))
dataset_path=next(p for p in protocol['inputs'] if p.endswith('matches_spatial.parquet'))
baseline_path=next(p for p in protocol['inputs'] if p.endswith('baseline_predictions.parquet'))
c=pd.read_parquet(canonical_path);d=pd.read_parquet(dataset_path);b=pd.read_parquet(baseline_path)
keys=set(zip(d.circuit,d.edition_id))
history=c.loc[[group=='tour' and (circuit,edition) in keys for group,circuit,edition in zip(c.source_group,c.circuit,c.tourney_id)]]
reproduced,_=extract_draw_load(history,d);load=pd.read_parquet(root/'draw_load_features.parquet')
pd.testing.assert_frame_equal(reproduced,load)
canonical=c.set_index('match_id',verify_integrity=True)
targets=d.set_index('match_id',verify_integrity=True)
for row in load.loc[load.draw_load_supported].itertuples():
    target=canonical.loc[row.match_id]
    for side,player in [('a',targets.loc[row.match_id,'player_a']),('b',targets.loc[row.match_id,'player_b'])]:
        for mid in json.loads(getattr(row,side+'_prior_match_ids')):
            prior=canonical.loc[mid]
            assert prior.tourney_id==target.tourney_id and prior.circuit==target.circuit and prior.source_group==target.source_group
            assert prior.winner_id==player and ROUND_ORDER[prior['round']]<ROUND_ORDER[target['round']] and mid!=row.match_id
joined=attach_baseline(d,b).merge(load,on='match_id',validate='one_to_one')
counts={}
for name,complete in [('main',False),('complete_observed_counters',True)]:
    report=json.loads((root/f'{name}_report.json').read_text());test=pd.read_parquet(root/f'{name}_predictions.parquet')
    eligible=joined.draw_load_supported & joined.both_have_prior_observed_play & joined.completed_standard & joined.baseline_probability.notna()
    if complete:eligible &= joined.observed_counters_complete
    train=joined.loc[eligible & joined.partition.eq('development_2024')]
    assert set(test.match_id)==set(joined.loc[eligible & joined.partition.eq('exploratory_2025'),'match_id'])
    assert not set(train.comparison_block_id)&set(test.comparison_block_id)
    for variant,features in [('coverage',CONTROL_FEATURES),('load',CONTROL_FEATURES+LOAD_FEATURES)]:
        model=DrawLoadCorrection(features);artifact=model.fit(train)
        assert artifact==report['artifacts'][variant]
        np.testing.assert_allclose(model.predict(test),test[variant+'_probability'],atol=1e-14)
    for variant,col in [('base','baseline_probability'),('base_plus_coverage','coverage_probability'),('base_plus_coverage_plus_load','load_probability')]:
        assert probability_metrics(test.y.astype(int).tolist(),test[col].astype(float).tolist())==report['metrics'][variant]
    counts[name]=dict(training=len(train),evaluation=len(test))
daily=json.loads((root/'strict_daily_feasibility.json').read_text())
assert daily['with_finite_completion_lower_bound']==0 and not daily['windows_3d_7d_ready']
assert all(sha(s['source_path'])==s['sha256'] for s in daily['archive_sources'])
frozen=json.loads(Path('data/tennis/extension_20261017/future_protocol.json').read_text())['artifacts']
assert len(frozen)==12 and all(sha(p)==s for p,s in frozen.items())
base=Path(__file__).resolve().parents[1]
assert sha(base/'tennis_engine/draw_load.py')==protocol['code_sha256']['draw_load.py']
assert sha(base/'scripts/run_draw_load_comparison.py')==protocol['code_sha256']['run_draw_load_comparison.py']

# Prioritize the remaining geography work without changing any pinned inputs.
registry=json.loads(Path('data/tennis/historical_coverage_20261018/registry.json').read_text())
counts_by_venue=d.loc[~d.target_coordinate_available].groupby('venue_id').size().to_dict()
queue=[dict(venue_id=v['venue_id'],name=v['name'],city=v.get('city'),country=v.get('country'),
    affected_target_matches=int(counts_by_venue.get(v['venue_id'],0)),status='coordinates_unverified')
    for v in registry['venues'] if v.get('lat') is None]
queue.sort(key=lambda r:(-r['affected_target_matches'],r['venue_id']))
assert len(queue)==88 and sum(r['affected_target_matches'] for r in queue)==730
(root/'geography_priority_queue.json').write_text(json.dumps(queue,indent=2))
audit=dict(schema='tennis-draw-load-delivery-audit-v1',created_at=datetime.now(timezone.utc).isoformat(),
    features_reproduced=True,earlier_round_precedence_verified=True,exact_common_intersections=True,
    training_artifacts_reproduced=True,metrics_recomputed=True,cohorts=counts,
    frozen_artifacts_verified=12,odds_credits_consumed=0,new_provider_calls=0,windows_3d_7d_ready=False,
    geography_unverified_entries=88,geography_affected_target_matches=730,
    files_sha256={p.name:sha(p) for p in root.iterdir() if p.is_file() and p.name not in ('.gitignore','delivery_audit.json')})
(root/'delivery_audit.json').write_text(json.dumps(audit,indent=2))
print(json.dumps({k:v for k,v in audit.items() if k!='files_sha256'},indent=2))
