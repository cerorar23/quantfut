import copy
import pytest
import numpy as np
from nba.minutes_repair import fit_width, widen, calibrated_forecast, project_team, team_scenarios

P = dict(train_season='2021-22', fit_cutoff='2022-07-01', scale_grid=[1, 1.5, 2], minimum_band_cases=2, target_coverage=.8)

def train_fixture():
    f = [dict(game_id=str(i), player_id=1, season='2021-22', date=f'2022-01-0{i+2}', history_max_date='2021-12-31', candidate_samples=[10,20,30], baseline_mean=20, actionable=False) for i in range(5)]
    s = [dict(game_id=r['game_id'], player_id=1, season=r['season'], date=r['date'], actual_regulation_minutes=35) for r in f]
    return f, s

def roster():
    return [dict(player_id=i, team_id=10, id_namespace='nba', samples=[10,20,30], active=True) for i in range(10)]

def test_train_fitting_width_and_application_support():
    f, s = train_fixture()
    fit = fit_width(f,s,P)
    assert fit['selections']['all']['scale']==2
    future=dict(f[0],date='2023-01-01')
    repaired=calibrated_forecast(future,fit)
    assert min(repaired['calibrated_samples'])>=0 and max(repaired['calibrated_samples'])<=48
    assert not repaired['actionable'] and not fit['validation_used_for_fitting']
    assert future['candidate_samples']==[10,20,30]

@pytest.mark.parametrize('kind',['season','future','identity','outcome','duplicate','history'])
def test_calibration_rejects_contamination(kind):
    f,s=train_fixture()
    if kind=='season':f[0]['season']='2025-26'
    if kind=='future':f[0]['date']=s[0]['date']='2023-01-01'
    if kind=='identity':s[0]['player_id']=2
    if kind=='outcome':s[0]['actual_regulation_minutes']=float('nan')
    if kind=='duplicate':f.append(copy.deepcopy(f[0]));s.append(copy.deepcopy(s[0]))
    if kind=='history':f[0]['history_max_date']=f[0]['date']
    with pytest.raises(ValueError):fit_width(f,s,P)

def test_training_calibrator_cannot_be_used_before_its_cut():
    f,s=train_fixture();fit=fit_width(f,s,P)
    with pytest.raises(ValueError):calibrated_forecast(f[0],fit)

def test_unattainable_coverage_is_explicit_not_passing():
    f,s=train_fixture()
    for row in f:row['candidate_samples']=[20,20,20]
    fit=fit_width(f,s,P)
    assert not fit['selections']['all']['train_target_met']

def test_projection_known_solution_dnp_and_minute_restriction():
    x=np.array([[40,40,40,40,40,40,30]],dtype=float)
    out=project_team(x,[0]*7,[48,48,48,48,48,10,0])
    np.testing.assert_allclose(out,[[46,46,46,46,46,10,0]],atol=1e-8)

def test_projector_invariants_over_diverse_vectors():
    rng=np.random.default_rng(8)
    out=project_team(rng.normal(24,40,size=(400,12)),[0]*12,[48]*12)
    assert out.min()>=0 and out.max()<=48
    np.testing.assert_allclose(out.sum(axis=1),240,atol=1e-8)
    np.testing.assert_allclose(project_team(out,[0]*12,[48]*12),out,atol=1e-8)

def test_joint_samples_conserve_team_and_reproduce_seed():
    players=roster();players[-1]['active']=False;players[0]['maximum_minutes']=20
    a=team_scenarios(players,draws=100,seed=23);b=team_scenarios(players,draws=100,seed=23)
    assert a==b and a['team_minutes_coherent'] and not a['availability_known']
    draws=np.array(a['draws'])
    np.testing.assert_allclose(draws.sum(axis=1),240,atol=1e-8)
    assert (draws[:,-1]==0).all() and (draws[:,0]<=20).all()

@pytest.mark.parametrize('kind',['underfive','restricted_capacity','duplicate','namespace','team','pretend_verified','nonfinite','DNP_minimum'])
def test_infeasible_or_unproved_scenarios_rejected(kind):
    players=roster();kwargs={}
    if kind=='underfive':players=players[:4]
    if kind=='restricted_capacity':
        for p in players:p['maximum_minutes']=20
    if kind=='duplicate':players[0]['player_id']=players[1]['player_id']
    if kind=='namespace':players[0]['id_namespace']='espn'
    if kind=='team':players[0]['team_id']=20
    if kind=='pretend_verified':kwargs['availability_kind']='verified_as_of'
    if kind=='nonfinite':players[0]['samples']=[float('inf')]
    if kind=='DNP_minimum':players[0].update(active=False,minimum_minutes=1)
    with pytest.raises(ValueError):team_scenarios(players,**kwargs)

def test_scale_one_preserves_distribution_and_clipping_is_exact():
    assert widen([0,5,48],1)==[0,5,48]
    assert widen([0,5,48],2)==[0,5,48]
