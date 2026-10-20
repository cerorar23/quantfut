"""Scientific evaluation invariants; fixtures here are artificial, never evidence."""
import copy,json
import numpy as np
import pandas as pd
import pytest
from test_paper_validation import setup,file,sha,results
from tennis_quality_v3.evaluation import MODELS,identity_review,reliability,compare,block_interval
from tennis_quality_v3.prospective import freeze,load,checksum,write_new,evaluate_future,seal_prediction


def protocol(s):
    p=s['root']/'quality.json'
    freeze(p,dict(evaluation_start='2026-10-20T00:00:00Z',evaluation_end='2027-01-01T00:00:00Z',
           artifacts={str(s['asset']):sha(s['asset'])}),created_at='2026-10-19T00:00:00Z')
    return p


def prediction(s,p):
    folder=s['root']/'quality-predictions';folder.mkdir(exist_ok=True)
    value=dict(event=s['event'],circuit='ATP',protocol_sha256=sha(p),artifacts=load(p)['artifacts'],
        sealed_at='2026-10-20T08:00:00Z',fixture_receipt=s['row']['fixture_receipt'],
        tournament_metadata=s['row']['tournament_metadata'],competition_id='test:2026',
        variants={m:.6 for m in MODELS})
    write_new(folder/'one.json',dict(value,payload_sha256=checksum(value)))
    return folder


def test_identity_quarantine_never_merges_distinct_ids():
    r=identity_review({'a':'María Smith','b':'Maria  Smith','c':'Other Player'})
    assert r['excluded_ids']==['a','b'] and r['automatic_merges']==0


def test_band_sides_are_selected_without_using_outcomes():
    r=reliability([0,1],[.2,.8],['t1','t2'])
    assert r['favourite_accuracy']==1 and r['bands'][3]['mean_forecast']==pytest.approx(.8)
    assert r['fixed_threshold_coverage'][2]['coverage']==1
    assert not r['bands'][3]['individual_forecast_certainty']


def test_probability_one_and_half_are_not_dropped():
    r=reliability([0,1],[.5,1.],['t1','t2'])
    assert r['bands'][0]['n']==1 and r['bands'][-1]['n']==1
    assert r['favourite_accuracy']==.5


def test_duplicating_observations_within_blocks_does_not_fake_precision():
    first=block_interval([0.,1.],['a','b'],draws=2000)
    repeated=block_interval([0.]*100+[1.]*100,['a']*100+['b']*100,draws=2000)
    assert first==repeated
    assert block_interval([1.,0.],['a','a']) is None


def test_all_success_small_band_cannot_report_perfect_bootstrap_certainty():
    r=reliability([1]*5,[.95]*5,['a','b','c','d','e'])
    band=r['bands'][-1]
    assert band['observed_hit_rate']==1
    assert band['block_hit_rate_ci95'] is None and band['iid_wilson_ci95'][0]<.6


def test_common_cohort_cannot_contain_duplicate_matches():
    f=pd.DataFrame([dict(match_id='same',y=1,period='2026-01-01',competition_id='t',**{m:.6 for m in MODELS})]*2)
    with pytest.raises(ValueError,match='Unique common'):compare(f,2,scope='test')


@pytest.mark.parametrize('probability',[float('nan'),float('inf'),1.1,True])
def test_invalid_probabilities_fail_instead_of_becoming_confidence(probability):
    with pytest.raises(ValueError):reliability([1],[probability],['t'])


def test_future_protocol_cannot_start_before_its_creation(setup):
    with pytest.raises(ValueError,match='future quality'):
        freeze(setup['root']/'bad.json',dict(evaluation_start='2026-10-19T00:00:00Z',evaluation_end='2027-01-01T00:00:00Z'),created_at='2026-10-20T00:00:00Z')


def test_changed_model_invalidates_even_an_empty_evaluation(setup):
    p=protocol(setup);setup['asset'].write_text('changed')
    with pytest.raises(ValueError,match='artifact'):load(p)


def test_results_do_not_enter_forecast_generation(setup):
    p=protocol(setup)
    with pytest.raises(ValueError,match='labels cannot enter'):
        seal_prediction(p,dict(y=1),setup['root']/'predictions')


def test_empty_future_sample_is_unknown_not_accredited(setup):
    p=protocol(setup);folder=setup['root']/'predictions';folder.mkdir();rfile=file(setup['root'],'empty.json',[])
    r=evaluate_future(p,folder,rfile,evaluated_at='2026-10-21T00:00:00Z')
    assert r['completed']==0 and not r['predictive_quality_accredited']
    assert r['by_circuit']['ATP']['models']['current_hybrid']['metrics']['log_loss'] is None


def test_comparison_universe_is_counted_separately_per_circuit(setup):
    p=protocol(setup);folder=prediction(setup,p)
    r=evaluate_future(p,folder,results(setup),evaluated_at='2026-10-20T12:00:00Z')
    assert r['completed']==1 and r['by_circuit']['ATP']['total_universe']==1
    assert r['by_circuit']['WTA']['total_universe']==0
    assert not r['by_circuit']['ATP']['predeclared_statistical_gate_passed']


def test_duplicate_seals_cannot_increase_independent_sample(setup):
    p=protocol(setup);folder=prediction(setup,p);(folder/'duplicate.json').write_bytes((folder/'one.json').read_bytes())
    r=evaluate_future(p,folder,results(setup),evaluated_at='2026-10-20T12:00:00Z')
    assert r['completed']==1 and len(r['rejected'])==1


def test_prediction_after_actual_start_is_rejected_even_if_locally_rehashed(setup):
    p=protocol(setup);folder=prediction(setup,p);rfile=results(setup)
    d=json.loads(rfile.read_text());d[0]['actual_start']='2026-10-20T07:59:59Z';rfile.write_text(json.dumps(d))
    r=evaluate_future(p,folder,rfile,evaluated_at='2026-10-20T12:00:00Z')
    assert r['completed']==0 and r['rejected']


def test_result_source_tamper_and_unverified_times_are_not_accepted(setup):
    p=protocol(setup);folder=prediction(setup,p);rfile=results(setup)
    d=json.loads(rfile.read_text());d[0]['actual_start']=None;rfile.write_text(json.dumps(d))
    r=evaluate_future(p,folder,rfile,evaluated_at='2026-10-20T12:00:00Z')
    assert r['completed']==0 and r['rejected']


def ready_forecast_fixture(s,monkeypatch,expire=False):
    import tennis_quality_v3.prospective as module
    names=file(s['root'],'data/models/ATP_current/model.json',dict(names={'a':'A','b':'B'}))
    identities=file(s['root'],'identities.json',dict(circuits={'ATP':dict(excluded_ids=[])}))
    reference=file(s['root'],'reference.json',dict(schema='tennis-welo-period-v1',weighted=True,ratings={'a':1500.,'b':1500.},last_block='2026-10-01'))
    p=s['root']/'operational-quality.json'
    freeze(p,dict(evaluation_start='2026-10-20T00:00:00Z',evaluation_end='2027-01-01T00:00:00Z',
      data_root=str(s['root']/'data'),improvements_root=str(s['root']/'pools'),identity_review_path=str(identities),
      reference_paths={'ATP':{name:str(reference) for name in ('weighted_elo','adaptive_elo')}},
      artifacts={str(x):sha(x) for x in (names,identities,reference)}),created_at='2026-10-19T00:00:00Z')
    moments=iter(['2026-10-20T08:00:00Z','2026-10-20T10:01:00Z' if expire else '2026-10-20T08:00:01Z'])
    monkeypatch.setattr(module,'now',lambda:next(moments))
    monkeypatch.setattr(module,'hybrid_forecast',lambda *a,**k:dict(serve={'unknown_effects':0},winner_A=.6,markov_A=.61,surface_elo_A=.59,calibrated_surface_elo_A=.58))
    event_input=dict(event=s['event'],circuit='ATP',player_ids=['a','b'],
       tournament_metadata=s['row']['tournament_metadata'],fixture_receipt=s['row']['fixture_receipt'])
    return p,event_input


def test_probability_only_forecast_can_be_sealed_without_quotes(setup,monkeypatch):
    p,event=ready_forecast_fixture(setup,monkeypatch)
    path=seal_prediction(p,event,setup['root']/'operational-predictions')
    record=json.loads(path.read_text())
    assert set(record['variants'])==set(MODELS) and not record['odds_used']
    assert record['sealed_at']=='2026-10-20T08:00:01Z'
    assert not record['individual_certainty']


def test_fixture_expiry_during_computation_prevents_a_late_seal(setup,monkeypatch):
    p,event=ready_forecast_fixture(setup,monkeypatch,expire=True)
    with pytest.raises(ValueError,match='expired during'):
        seal_prediction(p,event,setup['root']/'operational-predictions')
