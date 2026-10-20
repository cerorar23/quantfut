from dataclasses import replace
from datetime import datetime,timedelta,timezone
import hashlib

import numpy as np
import pytest

from tennis_engine.benchmark import BenchmarkCase,BenchmarkPrediction,BenchmarkResult
from tennis_engine.spatial_experiment import (ClockScenario,DayPair,SpatialTrialRow,SpatialExperiment,
    estimated_gap,local_scenario_time,UnavailableFeatures)
from tennis_engine.travel import Evidence,InterTournamentTravelExtractor,TournamentTransition
from tennis_engine.venues import VenueRegistry


FIT='2025-02-05T00:00:00Z'
EVAL='2025-02-20T00:00:00Z'


@pytest.fixture
def trial(tmp_path):
    path=tmp_path/'evidence.txt';path.write_text('synthetic test evidence, not real results')
    evidence=Evidence(str(path),hashlib.sha256(path.read_bytes()).hexdigest(),'2025-01-01T00:00:00Z')
    registry=VenueRegistry(tmp_path/'venues.sqlite')
    registry.add_source({'source_id':'s','url':'https://example.org/venue','received_at':evidence.received_at,
                         'source_path':str(path),'sha256':evidence.sha256})
    for identity,lat,lon,zone,height in [('china',31,121,'Asia/Shanghai',20),('near',48,3,'Europe/Paris',100),('target',48.8,2.3,'Europe/Paris',40)]:
        registry.register_venue({'venue_id':identity,'name':identity,'city':'test','country':'XX','timezone':zone,
            'lat':lat,'lon':lon,'altitude_m':height,'coordinate_scope':'venue_point','coordinate_precision_m':300,
            'recorded_at':'2025-01-02T00:00:00Z',
            'field_sources':{k:['s'] for k in ['name','city','country','timezone','coordinates','altitude_m']}})
    extractor=InterTournamentTravelExtractor(registry)
    def make(i,day):
        d=datetime.fromisoformat(day).replace(tzinfo=timezone.utc,hour=8)
        c=BenchmarkCase(str(i),str(i),'a','b',d.isoformat(),(d+timedelta(hours=4)).isoformat())
        r=BenchmarkResult(str(i),'a','b','completed',i%2,c.scheduled_start,(d+timedelta(hours=6)).isoformat(),(d+timedelta(hours=7)).isoformat())
        b=BenchmarkPrediction(c.case_id,'a','b',c.decision_at,.6)
        transitions=[];dates=[]
        for pid,site in [('a','china' if i%2 else 'near'),('b','near' if i%2 else 'china')]:
            transitions.append(TournamentTransition(pid,'prior'+pid,'target-edition',site,'target',c.scheduled_start,
                (evidence,),True,True,True,True))
            zone='Asia/Shanghai' if site=='china' else 'Europe/Paris'
            dates.append(DayPair((d-timedelta(days=3+(i%3 if pid=='a' else 0))).date().isoformat(),d.date().isoformat(),
                zone,'Europe/Paris','verified_actual_day','verified_scheduled_day',(evidence,)))
        return SpatialTrialRow(c,r,b,*transitions,*dates)
    train=[make(i,(datetime(2025,1,10)+timedelta(days=i)).date().isoformat()) for i in range(24)]
    test=[make(100+i,(datetime(2025,2,10)+timedelta(days=i)).date().isoformat()) for i in range(6)]
    yield SpatialExperiment(extractor),train,test
    registry.db.close()


def test_runs_three_variants_on_identical_cases_and_all_nine_scenarios(trial):
    experiment,train,test=trial
    report=experiment.run(train,test,fitted_at=FIT,evaluated_at=EVAL)
    assert report['status']=='evaluated' and report['n_train_common']==24
    assert report['comparison']['n_common']==6 and report['coverage']==1
    assert len(report['scenario_names'])==9 and len(report['comparison']['metrics'])==11
    assert {m['n'] for m in report['comparison']['metrics'].values()}=={6}
    assert report['hours_imputed_in_spatial_branch'] is False
    assert report['test_used_for_selection'] is False


def test_test_labels_do_not_change_training_scaling_or_coefficients(trial):
    experiment,train,test=trial
    a=experiment.run(train,test,fitted_at=FIT,evaluated_at=EVAL)
    changed=[replace(r,result=replace(r.result,y=0)) for r in test]
    b=experiment.run(train,changed,fitted_at=FIT,evaluated_at=EVAL)
    assert a['artifacts']==b['artifacts']
    assert a['comparison']['metrics']['base']['log_loss']!=b['comparison']['metrics']['base']['log_loss']
    # Also perturb target covariates; fit and scale must still be identical.
    changed=[replace(r,transition_a=replace(r.transition_a,previous_venue_id='near'),
                     days_a=replace(r.days_a,previous_timezone='Europe/Paris')) for r in test]
    c=experiment.run(train,changed,fitted_at=FIT,evaluated_at=EVAL)
    assert a['artifacts']==c['artifacts']


def test_scaling_equals_training_rms_only(trial):
    experiment,train,test=trial
    report=experiment.run(train,test,fitted_at=FIT,evaluated_at=EVAL)
    x=np.stack([experiment._features(r)['spatial'] for r in train])
    expected=np.sqrt(np.mean(x*x,axis=0));expected[expected==0]=1
    assert report['artifacts']['spatial']['rms_train']==pytest.approx(expected)


def test_scenarios_perturb_players_independently_not_a_cancelling_shared_shift(trial):
    experiment,_,test=trial
    features=experiment._features(test[0]);gaps=[x[-1] for name,x in features.items() if name!='spatial']
    assert max(gaps)>min(gaps)


def test_main_branch_ignores_scenario_hours_and_preserves_swap_symmetry(trial):
    experiment,_,test=trial;r=test[0]
    a=experiment._features(r)
    reverse=replace(r,case=replace(r.case,player_a='b',player_b='a'),
        transition_a=r.transition_b,transition_b=r.transition_a,days_a=r.days_b,days_b=r.days_a)
    b=experiment._features(reverse)
    for name in a:assert a[name]==pytest.approx(-b[name])
    other=SpatialExperiment(experiment.extractor,scenarios=(ClockScenario(5,21,22),))
    assert other._features(r)['spatial']==pytest.approx(a['spatial'])


def test_week_date_is_not_imputed_into_a_match_day(trial):
    experiment,train,test=trial
    changed=[replace(r,days_a=replace(r.days_a,exit_precision='tournament_week')) for r in test]
    result=experiment.run(train,changed,fitted_at=FIT,evaluated_at=EVAL)
    assert result['status']=='insufficient_common_training_or_test_sample'
    assert result['comparison'] is None and result['coverage']==0


def test_partial_missingness_uses_common_test_intersection(trial):
    experiment,train,test=trial
    test[0]=replace(test[0],days_b=None)
    result=experiment.run(train,test,fitted_at=FIT,evaluated_at=EVAL)
    assert result['comparison']['n_common']==5
    assert {m['n'] for m in result['comparison']['metrics'].values()}=={5}


def test_future_label_and_train_test_overlap_are_rejected(trial):
    experiment,train,test=trial
    with pytest.raises(ValueError,match='labels'):
        experiment.run([replace(train[0],result=replace(train[0].result,available_at=FIT))]+train[1:],test,fitted_at=FIT,evaluated_at=EVAL)
    with pytest.raises(ValueError,match='overlap'):experiment.run(train,[train[0]],fitted_at=FIT,evaluated_at=EVAL)


def test_missing_training_does_not_copy_baseline_as_candidate(trial):
    experiment,_,test=trial
    result=experiment.run([],test,fitted_at=FIT,evaluated_at=EVAL)
    assert result['status']=='insufficient_common_training_or_test_sample'
    assert result['artifacts']=={} and result['comparison'] is None


def test_local_dst_and_day_availability_are_not_silently_imputed(trial):
    with pytest.raises(UnavailableFeatures):local_scenario_time('2025-03-30',2,'Europe/Paris')
    with pytest.raises(UnavailableFeatures):local_scenario_time('2025-10-26',2,'Europe/Paris')
    _,_,test=trial
    pair=replace(test[0].days_a,previous_exit_day='2025-02-10')
    with pytest.raises(UnavailableFeatures,match='fully_before'):
        estimated_gap(pair,ClockScenario(0,14),'2025-02-10T10:00:00Z')


def test_verified_known_hours_are_preserved_in_every_scenario(trial):
    _,_,test=trial
    pair=replace(test[0].days_a,previous_exit_day='2025-02-07',actual_exit_at='2025-02-07T12:00:00Z',
                 known_debut_at='2025-02-10T12:00:00Z')
    assert estimated_gap(pair,ClockScenario(12,10),'2025-02-10T08:00:00Z')==3
    assert estimated_gap(pair,ClockScenario(23,18),'2025-02-10T08:00:00Z')==3
