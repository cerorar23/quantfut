"""Execute real-archive feasibility and the three-model runner without invented rows.

Run from the main data workspace. This script does not request new API data or
turn archived tournament-week dates into event timestamps.
"""
from collections import Counter
import argparse
from datetime import datetime,timezone
import hashlib,json,sqlite3,sys
from pathlib import Path

sys.path.insert(0,str(Path('.local/tennis_next').resolve() if Path(__file__).parent.name=='.local' else Path(__file__).resolve().parents[1]))
from tennis_engine.operations import utc
from tennis_engine.spatial_experiment import SpatialExperiment,sensitivity_grid
from tennis_engine.travel import InterTournamentTravelExtractor
from tennis_engine.venues import VenueRegistry


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf8'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('data/tennis/spatial_trial_20261018_v3'))
    root=parser.parse_args().output
    root.mkdir(exist_ok=True)
    if (root/'report.json').exists():raise ValueError('Immutable run exists; review its report rather than overwrite it')
    fitted_at=datetime.now(timezone.utc).isoformat()
    seed_path=Path('data/tennis/coordinates_20261018/registry_seed_elevation.json')
    seed=read(seed_path)
    for source in seed['sources']:
        if digest(source['source_path'])!=source['sha256']:raise ValueError('Venue source changed')
    coverage_path=Path('data/tennis/full_20261016/canonical/coverage.json');coverage=read(coverage_path)
    earliest=min((v['recorded_at'] for v in seed['venues'] if v.get('lat') is not None),key=utc)
    # The entire historical archive ends before even the first coordinate
    # registration. No archive row can have used these registry versions then.
    if not coverage['as_of']<utc(earliest).date().isoformat():
        raise ValueError('Temporal archive gate changed; implement a row-level join before proceeding')
    calendar_source=next(s for s in seed['sources'] if s['source_id']=='api_upcoming')
    calendar=read(calendar_source['source_path'])['result']
    states_path=Path('data/tennis/state_capture_20261017/states.sqlite').resolve()
    db=sqlite3.connect(states_path.as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    latest={r['event_id']:dict(r) for r in db.execute('SELECT * FROM observations WHERE received_at<? ORDER BY received_at',(fitted_at,))}
    db.close()
    target_ids={'api_tennis:'+str(row['event_key']) for row in calendar}
    completed_targets=[latest[k] for k in target_ids if k in latest and latest[k]['state']=='completed']
    readiness_path=Path('data/tennis/coordinates_20261018/travel_input_readiness.json');readiness=read(readiness_path)
    if readiness['verified_transitions_ready']!=0 or completed_targets:
        raise ValueError('New eligible evidence detected; build reviewed rows rather than reuse the empty-cohort audit')
    frozen_path=Path('data/tennis/extension_20261017/future_protocol.json');frozen=read(frozen_path)
    for path,sha in frozen['artifacts'].items():
        if digest(path)!=sha:raise ValueError('Frozen model artifact changed')
    registry=VenueRegistry(Path('data/tennis/venues_20261017/venues.sqlite'))
    runner=SpatialExperiment(InterTournamentTravelExtractor(registry))
    evaluated_at=datetime.now(timezone.utc).isoformat()
    # Both cohorts are empty as a result of the proven gates above, not because
    # unavailable features or labels have been replaced with synthetic values.
    result=runner.run([],[],fitted_at=fitted_at,evaluated_at=evaluated_at)
    registry.db.close()
    audit={'canonical_archive_matches':coverage['canonical_matches'],'archive_as_of':coverage['as_of'],
           'first_coordinate_registration_at':earliest,'historical_rows_with_available_spatial_registry':0,
           'archived_target_matches':len(calendar),'target_completed_results_in_captured_state_store':len(completed_targets),
           'verified_transitions_in_readiness_audit':readiness['verified_transitions_ready'],
           'candidate_player_fixture_rows':readiness['player_fixture_rows_with_candidate_history'],
           'cached_states':dict(Counter(r['state'] for r in latest.values())),
           'readiness_audit_as_of':readiness['as_of'],'new_sports_api_calls':0,'odds_api_credits':0}
    protocol={'schema':'tennis-spatial-trial-protocol-v1','created_at':fitted_at,'label':'experimental',
        'branches':['base','base_plus_verified_spatial','experimental_spatial_plus_estimated_gap'],
        'spatial_features':['distance_km_A_minus_B','altitude_change_m_A_minus_B','timezone_clock_delta_hours_A_minus_B'],
        'spatial_hours_imputed':False,'required_dates_for_scenarios':'verified actual exit day; verified target debut day',
        'scenario_exit_hour_assignment':'independent by canonical player-ID order, invariant to A/B swap',
        'scenarios':[{'name':s.name,'exit_hour_lower_player_id':s.exit_hour,
                      'exit_hour_higher_player_id':s.other_exit_hour,'common_debut_hour':s.debut_hour} for s in sensitivity_grid()],
        'transformations':'training-only RMS; ridge logistic offset on supplied pre-match base probabilities',
        'ridge':1.,'minimum_training_rows':20,'minimum_is_not_a_power_guarantee':True,
        'evaluation':'same completed pre-match cohort for all branches and scenarios; log-loss, Brier, ECE10',
        'selection_on_test':False,'all_scenarios_reported':True,'imputed_gap_is_actual_rest':False,
        'protected_existing_holdout':[frozen['evaluation_start'],frozen['evaluation_end']],
        'existing_holdout_repurposed_for_new_model_selection':False,
        'prospective_inference_requires_a_new_untouched_future_period_after_training':True,
        'source_sha256':{str(p):digest(p) for p in [seed_path,coverage_path,readiness_path,frozen_path]},
        'runner_code_sha256':digest(Path(sys.modules[SpatialExperiment.__module__].__file__))}
    report={**result,'data_audit':audit,'models_trained':0,'metrics_computed_on_real_matches':False,
            'model_metrics':{k:{'n':0,'log_loss':None,'brier':None,'ece':None} for k in protocol['branches']},
            'sensitivity_executed_on_real_matches':False,'frozen_model_hashes_verified':len(frozen['artifacts']),
            'blocking_stage':'data_eligibility','coverage_of_archived_target_universe':0.0}
    for name,value in [('protocol.json',protocol),('report.json',report)]:
        (root/name).write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf8')
    (root/'.gitignore').write_text('*\n!.gitignore\n')
    print(json.dumps({'status':report['status'],'n_train_common':report['n_train_common'],'n_test_common':report['n_test_common'],
                      'archived_targets':len(calendar),'models_trained':0,'frozen_hashes_verified':len(frozen['artifacts'])}))


if __name__=='__main__':main()
